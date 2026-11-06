"""B站表情支持：拉表情索引 -> 下载到本地缓存 -> 提供 HTML 片段。

弹幕里的表情在原始文本里就是 `[笑哭]` 这样的 token，
所以只要把 token 换成 <img>，QTextBrowser 就能直接显示。
"""
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, Signal

import bili

CACHE_DIR = os.path.expanduser("~/.cache/bili-danmaku/emotes")
TOKEN_RE = re.compile(r"\[[^\[\]\s]{1,16}\]")
EMOJI_H = 18  # 显示高度(px)


def _norm(name):
    """去掉表情名外面可能多余的方括号：'[[花]]' -> '花'。"""
    name = str(name or "").strip()
    while len(name) > 1 and name.startswith("[") and name.endswith("]"):
        name = name[1:-1].strip()
    return name


def _token(name):
    name = _norm(name)
    return "[" + name + "]" if name else ""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _png_size(path):
    """不依赖 PIL，直接读 PNG 头拿宽高。"""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w = int.from_bytes(head[16:20], "big")
            h = int.from_bytes(head[20:24], "big")
            return w, h
    except Exception:
        pass
    return 0, 0


class EmoteStore(QObject):
    ready = Signal()

    def __init__(self, room_id):
        super().__init__()
        self.room_id = room_id
        self.map = {}       # 全部表情 token -> (本地路径, 宽, 高)
        self.live = {}      # 只含直播间通用表情：这类发出去观众端才会显示成图片
        self._bare = {}     # 表情名 -> token（整条消息只有一个表情时用）
        os.makedirs(CACHE_DIR, exist_ok=True)
        threading.Thread(target=self._load, daemon=True).start()

    # ---------- 拉取 ----------
    def _load(self):
        idx = {}
        live_tokens = set()
        try:
            s = bili.new_session()
        except Exception:
            return
        # 1) 评论区表情包（小黄脸/小电视等），token 形如 [笑哭]
        try:
            j = bili.req(s, "https://api.bilibili.com/x/emote/user/panel/web",
                         {"business": "reply"})
            for pkg in (j.get("data") or {}).get("packages") or []:
                for e in pkg.get("emote") or []:
                    t, u = _token(e.get("text")), e.get("url")
                    if t and u:
                        idx.setdefault(t, u)
        except Exception:
            pass
        # 2) 直播间通用表情，token 形如 [啊]
        try:
            j = bili.req(
                s, "https://api.live.bilibili.com/xlive/web-ucenter/v2/emoticon/GetEmoticons",
                {"platform": "pc", "room_id": self.room_id})
            for pkg in (j.get("data") or {}).get("data") or []:
                for e in pkg.get("emoticons") or []:
                    u = e.get("url")
                    tok = _token(e.get("emoji"))
                    if tok and u:
                        idx.setdefault(tok, u)
                        live_tokens.add(tok)
                        self._bare.setdefault(_norm(e.get("emoji")), tok)
        except Exception:
            pass
        if not idx:
            return

        # 3) 并发下载，附带到缓存的直接跳过
        items = list(idx.items())
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda kv: (kv[0], self._fetch(kv[1])), items))
        m = {}
        for token, path in results:
            if path:
                w, h = _png_size(path)
                m[token] = (path, w or EMOJI_H, h or EMOJI_H)
        self.map = m          # 一次性替换，避免边下边改
        self.live = {t: v for t, v in m.items() if t in live_tokens}
        if m:
            self.ready.emit()

    def _fetch(self, url):
        name = re.sub(r"[^0-9a-zA-Z]+", "", url.rsplit("/", 1)[-1])[:24]
        if not name:
            name = str(abs(hash(url)))
        path = os.path.join(CACHE_DIR, name if name.endswith(".png") else name + ".png")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
        try:
            import requests
            r = requests.get(url, timeout=10, headers={
                "User-Agent": bili.UA,
                "Referer": "https://www.bilibili.com/",
            })
            if r.status_code == 200 and r.content:
                with open(path, "wb") as f:
                    f.write(r.content)
                return path
        except Exception:
            return None
        return None

    # ---------- 渲染 ----------
    def _img(self, token):
        path, w, h = self.map[token]
        width = max(1, round(EMOJI_H * (w / h))) if h else EMOJI_H
        return ('<img src="file://%s" width="%d" height="%d" '
                'style="vertical-align:middle">' % (path, width, EMOJI_H))

    def render(self, text):
        """把弹幕文本转成带表情图片的 HTML（已做转义）。"""
        text = str(text or "")
        if not text:
            return ""
        bare = self._bare.get(text.strip())
        if bare and bare in self.map:
            return self._img(bare)
        out = []
        pos = 0
        for m in TOKEN_RE.finditer(text):
            out.append(esc(text[pos:m.start()]))
            tok = m.group(0)
            out.append(self._img(tok) if tok in self.map else esc(tok))
            pos = m.end()
        out.append(esc(text[pos:]))
        return "".join(out)
