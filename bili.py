import hashlib, time, urllib.parse
import requests

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")

MIXIN = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
         33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
         61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62,
         11, 36, 20, 34, 44, 52]


def load_cookie(path=None):
    """cookie 顺序: 环境变量 > ~/.config/bili-danmaku/cookie.txt > 项目目录"""
    import os
    cands = []
    if path:
        cands.append(path)
    if os.environ.get("BILI_DANMAKU_COOKIE"):
        cands.append(os.environ["BILI_DANMAKU_COOKIE"])
    cands.append(os.path.expanduser("~/.config/bili-danmaku/cookie.txt"))
    cands.append("/data/bili-danmaku/cookie.txt")
    raw = None
    for p in cands:
        try:
            raw = open(p, encoding="utf-8").read().strip()
            break
        except Exception:
            continue
    if not raw:
        return {}
    out = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("cookie:"):
            line = line.split(":", 1)[1]
        elif ":" in line and "=" not in line.split(":", 1)[0]:
            continue
        for part in line.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def new_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Referer": "https://live.bilibili.com/",
        "Origin": "https://live.bilibili.com",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    ck = load_cookie()
    for k, v in ck.items():
        s.cookies.set(k, v, domain=".bilibili.com")
    try:
        s.get("https://www.bilibili.com/", timeout=10)
    except Exception:
        pass
    return s


def get_mixin_key(s):
    j = req(s, "https://api.bilibili.com/x/web-interface/nav")
    wbi = j.get("data", {}).get("wbi_img") or {}
    img = wbi.get("img_url", "").rsplit("/", 1)[-1].split(".")[0]
    sub = wbi.get("sub_url", "").rsplit("/", 1)[-1].split(".")[0]
    raw = img + sub
    return "".join(raw[i] for i in MIXIN)[:32]


def wbi_sign(params, mixin_key):
    params = dict(params)
    params["wts"] = int(time.time())
    items = sorted(params.items())
    query = urllib.parse.urlencode(items)
    params["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return params


def get_danmu_info(s, room_id):
    mk = get_mixin_key(s)
    p = wbi_sign({"id": room_id, "type": 0}, mk)
    r = req(s, "https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo",
            p)
    return r, dict(s.cookies)


def send_danmaku(s, room_id, msg, color=16777215, mode=1, fontsize=25):
    """发一条弹幕。返回 (是否成功, 提示信息)。"""
    jct = dict(s.cookies).get("bili_jct", "")
    if not jct:
        return False, "没有登录 cookie（缺 bili_jct），先填 cookie"
    data = {
        "bubble": "0", "msg": msg, "color": str(color), "mode": str(mode),
        "fontsize": str(fontsize), "rnd": str(int(time.time())),
        "roomid": str(room_id), "csrf": jct, "csrf_token": jct,
        "reply_mid": "0", "reply_attr": "0",
    }
    try:
        j = s.post("https://api.live.bilibili.com/msg/send", data=data,
                   timeout=10).json()
    except Exception as e:
        return False, "网络错误: %s" % e
    if j.get("code") == 0:
        return True, "已发送"
    return False, j.get("message") or ("错误码 %s" % j.get("code"))


def req(s, url, params=None, tries=2, timeout=8):
    last = None
    for i in range(tries):
        try:
            return s.get(url, params=params, timeout=timeout).json()
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("请求失败: %s (%s)" % (url.rsplit('/', 1)[-1], last))


if __name__ == "__main__":
    s = new_session()
    j, ck = get_danmu_info(s, 31641927)
    print(j.get("code"), j.get("message"))
    if j.get("code") == 0:
        print([h["host"] for h in j["data"]["host_list"]])
        print("cookies:", ck)
