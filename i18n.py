"""界面文案：系统语言不是中文就自动切成英文。

判断顺序：BILI_DANMAKU_LANG > LC_ALL > LC_MESSAGES > LANG，
都没有或不是 zh* 就用英文。
"""
import os

_EN = {
    # 窗口 / 标题
    "B站弹幕": "Bilibili Danmaku",
    "连接中…": "Connecting…",
    "正在连接…": "Connecting…",
    "正在重连…": "Reconnecting…",
    "直播间": "Room",

    # 状态
    "直播中": "Live",
    "未开播": "Offline",
    "人气 %s": "Popularity %s",
    "%s · 看过 %s": "%s · %s views",
    "在线榜：": "Top: ",
    "连接异常，20 秒后重连": "Connection lost, retrying in 20s",

    # 弹幕区
    "%s 进入直播间": "%s entered",
    "已发送：%s": "Sent: %s",
    "⚠ 发送失败：%s": "⚠ Send failed: %s",
    "未填写Cookie": "No cookie set",
    "未填写Cookie（右键 → 填 / 改 cookie…）":
        "No cookie set (right-click → set cookie…)",
    "表情还没加载完": "Emotes are still loading",

    # 输入框
    "发条弹幕…（回车发送）": "Send a comment… (Enter)",
    "插入表情": "Insert emote",

    # 右键菜单
    "换个直播间…": "Change room…",
    "填 / 改 cookie…": "Set / change cookie…",
    "重新连接": "Reconnect",
    "显示进场消息": "Show enter messages",
    "清屏": "Clear",
    "退出": "Quit",

    # 对话框
    "换房间": "Change room",
    "直播间号": "Room ID",
    "直播间号：": "Room ID:",
    "输入直播间号：": "Enter room ID:",
    "登录 cookie": "Login cookie",
    "把浏览器里请求头那一整行 Cookie 粘进来\n（至少要含 SESSDATA）：":
        "Paste the whole Cookie header line from your browser\n"
        "(must contain SESSDATA):",
}


def pref_path():
    d = os.path.join(os.path.expanduser("~"), ".config", "bili-danmaku")
    return os.path.join(d, "lang.txt")


def _saved():
    """界面上手动选过的语言。"""
    try:
        v = open(pref_path(), encoding="utf-8").read().strip().lower()
        if v in ("zh", "en"):
            return v
    except Exception:
        pass
    return ""


def _from_env():
    for key in ("BILI_DANMAKU_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(key)
        if v and v.strip():
            return "zh" if v.strip().lower().startswith("zh") else "en"
    return "en"        # 没设置语言 = 非中文，走英文


def _detect():
    return os.environ.get("BILI_DANMAKU_LANG", "").strip().lower().startswith("zh") \
        if os.environ.get("BILI_DANMAKU_LANG") else \
        (_saved() or _from_env()) == "zh"


_zh = _detect()


def lang():
    return "zh" if _zh else "en"


def set_lang(code):
    """切换语言并记到配置文件，返回是否真的变了。"""
    global _zh
    new = (code == "zh")
    changed = new != _zh
    _zh = new
    try:
        os.makedirs(os.path.dirname(pref_path()), exist_ok=True)
        with open(pref_path(), "w", encoding="utf-8") as f:
            f.write("zh\n" if _zh else "en\n")
    except Exception:
        pass
    return changed


def is_english():
    return not _zh


def tr(text):
    """取界面文案；中文环境原样返回。"""
    if _zh:
        return text
    return _EN.get(text, text)
