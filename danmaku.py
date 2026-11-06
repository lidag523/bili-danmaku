"""B站直播弹幕客户端: 弹幕 / 进场 / 人气 / 看过人数"""
import json
import base64
import struct
import threading
import time
import zlib

import requests
import websocket

from bili import UA, new_session, get_danmu_info, req
from pb import fields

OP_HEARTBEAT = 2
OP_HEARTBEAT_REPLY = 3
OP_MESSAGE = 5
OP_AUTH = 7
OP_AUTH_REPLY = 8


def _brotli(data):
    try:
        import brotli
        return brotli.decompress(data)
    except Exception:
        return b""


def parse_packets(data):
    """拆包, 返回 [(op, body_bytes), ...]"""
    out = []
    while len(data) >= 16:
        plen, hlen, ver, op, _ = struct.unpack(">IHHII", data[:16])
        if plen < hlen or plen > len(data):
            break
        body = data[hlen:plen]
        data = data[plen:]
        if ver == 2:
            out.extend(parse_packets(zlib.decompress(body)))
        elif ver == 3:
            out.extend(parse_packets(_brotli(body)))
        else:
            out.append((op, body))
    return out


def make_packet(op, body: bytes):
    return struct.pack(">IHHII", 16 + len(body), 16, 1, op, 1) + body


def find_reply_uname(node):
    """在整个消息里递归找非空的 reply_uname（它藏在 extra 的 JSON 字符串里）。"""
    if isinstance(node, dict):
        v = node.get("reply_uname")
        if isinstance(v, str) and v.strip():
            return v.strip()
        for v in node.values():
            r = find_reply_uname(v)
            if r:
                return r
    elif isinstance(node, list):
        for v in node:
            r = find_reply_uname(v)
            if r:
                return r
    elif isinstance(node, str):
        t = node.strip()
        if t.startswith("{") and "reply_uname" in t:
            try:
                return find_reply_uname(json.loads(t))
            except Exception:
                return ""
    return ""


class DanmakuClient:
    """后台线程收弹幕, 通过回调抛事件"""

    def __init__(self, room_id, on_event):
        self.uid_input = room_id
        self.room_id = None
        self.on_event = on_event
        self.ws = None
        self._stop = threading.Event()
        self._hb = None
        self.thread = None

    # ---------- 对外 ----------
    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop.set()
        ws, self.ws = self.ws, None
        if ws:
            threading.Thread(target=self._safe_close, args=(ws,),
                             daemon=True).start()

    @staticmethod
    def _safe_close(ws):
        try:
            ws.close()
        except Exception:
            pass

    # ---------- 内部 ----------
    def _emit(self, kind, **kw):
        try:
            self.on_event(kind, kw)
        except Exception:
            pass

    def _prepare(self):
        s = new_session()
        r = req(s, "https://api.live.bilibili.com/room/v1/Room/room_init",
                {"id": self.uid_input})
        self.room_id = r["data"]["room_id"]
        info = req(s, "https://api.live.bilibili.com/room/v1/Room/get_info",
                   {"room_id": self.room_id})
        if info.get("code") == 0:
            d = info["data"]
            self._emit("room", title=d.get("title", ""),
                       owner=d.get("uid", 0), online=d.get("online", 0),
                       live=d.get("live_status", 0))
        j, cookies = get_danmu_info(s, self.room_id)
        if j.get("code") != 0:
            raise RuntimeError("getDanmuInfo 失败: %s" % j)
        hosts = []
        for h in j["data"]["host_list"]:
            if h["host"] not in hosts:
                hosts.append(h["host"])
        token = j["data"]["token"]
        buvid = cookies.get("buvid3", "")
        try:
            uid = int(cookies.get("DedeUserID") or 0)
        except Exception:
            uid = 0
        return hosts, token, buvid, uid

    def _heartbeat(self):
        while not self._stop.is_set():
            try:
                self.ws.send(make_packet(OP_HEARTBEAT, b"[object Object]"),
                             opcode=websocket.ABNF.OPCODE_BINARY)
            except Exception:
                return
            self._stop.wait(25)

    def _run(self):
        try:
            hosts, token, buvid, uid = self._prepare()
        except Exception as e:
            self._emit("error", msg=str(e))
            return
        self._emit("status", msg="连接中")
        self.ws = None
        for attempt in range(2):
            for host in hosts:
                if self._stop.is_set():
                    return
                try:
                    self.ws = websocket.create_connection(
                        "wss://%s/sub" % host, timeout=5,
                        origin="https://live.bilibili.com")
                    break
                except Exception as e:
                    self._emit("status", msg="重试中 %s" % host.split(".")[0])
            if self.ws:
                break
            if attempt == 0:
                time.sleep(1)
        if not self.ws:
            self._emit("error", msg="所有弹幕服务器都连不上")
            return

        self.ws.settimeout(45)
        auth = {"uid": uid, "roomid": self.room_id, "protover": 3,
                "platform": "web", "type": 2, "key": token, "buvid": buvid}
        self.ws.send(make_packet(OP_AUTH, json.dumps(auth).encode()),
                     opcode=websocket.ABNF.OPCODE_BINARY)
        self._hb = threading.Thread(target=self._heartbeat, daemon=True)
        self._hb.start()

        while not self._stop.is_set():
            try:
                raw = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                # 房间安静时没消息是正常的, 心跳还在跑
                continue
            except Exception as e:
                if not self._stop.is_set():
                    self._emit("error", msg="断开: %s" % e)
                return
            if isinstance(raw, str):
                continue
            for op, body in parse_packets(raw):
                if op == OP_HEARTBEAT_REPLY and len(body) >= 4:
                    self._emit("popularity",
                               value=struct.unpack(">I", body[:4])[0])
                elif op == OP_AUTH_REPLY:
                    self._emit("status", msg="已连接")
                elif op == OP_MESSAGE:
                    self._handle(body)

    def _handle(self, body):
        try:
            j = json.loads(body.decode("utf-8"))
        except Exception:
            return
        # cmd 常带 ":12345" 后缀，先剥掉，否则下面 == 比较会失配
        cmd = (j.get("cmd", "") or "").split(":")[0]
        if cmd == "DANMU_MSG":
            info = j.get("info") or []
            try:
                text = info[1]
                user = info[2][1]
                admin = bool(info[2][2])
            except Exception:
                return
            reply = find_reply_uname(j)
            self._emit("danmaku", user=user, text=text, admin=admin,
                       reply=reply)
        elif cmd == "INTERACT_WORD":
            d = j.get("data") or {}
            if d.get("msg_type") == 1:
                self._emit("enter", user=d.get("uname", ""), uid=d.get("uid"))
        elif cmd == "WATCHED_CHANGE":
            d = j.get("data") or {}
            self._emit("watched", text=d.get("text_small", ""))
        elif cmd == "INTERACT_WORD_V2":
            d = j.get("data") or {}
            try:
                raw = base64.b64decode(d.get("pb") or "")
            except Exception:
                return
            uid = name = None
            msg_type = 0
            for fno, v in fields(raw):
                if fno == 1 and not isinstance(v, bytes):
                    uid = v
                elif fno == 2 and isinstance(v, bytes):
                    name = v.decode("utf-8", "ignore")
                elif fno == 5 and not isinstance(v, bytes):
                    msg_type = v
            if msg_type == 1 and name:
                self._emit("enter", user=name, uid=uid)
        elif cmd == "ONLINE_RANK_V3":
            d = j.get("data") or {}
            try:
                raw = base64.b64decode(d.get("pb") or "")
            except Exception:
                return
            users = []
            for fno, v in fields(raw):
                if fno != 3 or not isinstance(v, bytes):
                    continue
                uid = name = score = rank = None
                for a, b in fields(v):
                    if a == 1 and not isinstance(b, bytes):
                        uid = b
                    elif a == 3 and isinstance(b, bytes):
                        score = b.decode("utf-8", "ignore")
                    elif a == 4 and isinstance(b, bytes):
                        name = b.decode("utf-8", "ignore")
                    elif a == 5 and not isinstance(b, bytes):
                        rank = b
                if name:
                    users.append({"name": name, "score": score or "",
                                  "rank": rank or 99})
            users.sort(key=lambda u: u["rank"])
            self._emit("rank", users=users[:3])
        elif cmd == "ONLINE_RANK_COUNT":
            d = j.get("data") or {}
            self._emit("online_rank", count=d.get("count", 0))
        elif cmd == "ONLINE_RANK_V2":
            lst = (j.get("data") or {}).get("list") or []
            self._emit("rank", users=[
                {"name": u.get("uname", ""), "score": u.get("score", "")}
                for u in lst[:3]])
        elif cmd == "SEND_GIFT":
            d = j.get("data") or {}
            self._emit("gift", user=d.get("uname", ""),
                       action=d.get("action", ""), gift=d.get("giftName", ""))
