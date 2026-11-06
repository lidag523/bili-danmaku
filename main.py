#!/usr/bin/env python3
"""B站直播弹幕悬浮窗 (Linux / PySide6)"""
import sys
import time
import logging
import threading
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import Qt, QObject, Signal, QPoint, QEvent
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QAction
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QTextBrowser, QPushButton, QMenu,
                               QInputDialog, QSizeGrip, QLineEdit)

from danmaku import DanmakuClient
from emotes import EmoteStore

MAX_LINES = 60
MAX_ENTER = 4      # 进场消息最多留几条
ENTER_H = 88       # 进场区域高度(px)
COLORS = ["#7fb2ff", "#8ee6a2", "#ffd479", "#ff9ecb", "#b9a2ff",
          "#7fe3e3", "#ffab8f", "#c8e08b"]


def color_of(name):
    return COLORS[sum(map(ord, name or "?")) % len(COLORS)]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


import os

log = logging.getLogger("bili-danmaku")


def setup_log():
    d = os.path.expanduser("~/.cache/bili-danmaku")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "app.log")
    h = RotatingFileHandler(path, maxBytes=512 * 1024, backupCount=2,
                            encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)
    log.propagate = False
    return path


def conf_dir():
    d = os.path.expanduser("~/.config/bili-danmaku")
    os.makedirs(d, exist_ok=True)
    return d


def conf_path():
    return os.path.join(conf_dir(), "cookie.txt")


class Bridge(QObject):
    event = Signal(str, dict)


class DanmakuWindow(QWidget):
    def __init__(self, room):
        super().__init__()
        self.room = room
        self.lines = []
        self.enter_lines = []
        self._show_enter = True
        self.popularity = 0
        self.watched = ""
        self.live = 0
        self._drag = None
        self._online = 0

        self.setWindowTitle("B站弹幕")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.resize(360, 520)
        self.setMinimumSize(240, 240)
        self._build_ui()

        self.bridge = Bridge()
        self.bridge.event.connect(self.on_event)
        self.emotes = EmoteStore(room)
        self.emotes.ready.connect(self.render)
        conf_dir()
        self.client = DanmakuClient(room, lambda k, w: self.bridge.event.emit(k, w))
        self.client.start()

        self.clock = self.startTimer(1000)
        self._apply_place()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(6)
        self.title = QLabel("连接中…")
        self.title.setStyleSheet("color:#eaf2ff;font-size:13px;font-weight:600;")
        head.addWidget(self.title, 1)

        self.count = QLabel("--")
        self.count.setStyleSheet("color:#9fd4ff;font-size:12px;")
        head.addWidget(self.count)

        close = QPushButton("✕")
        close.setFixedSize(20, 20)
        close.setCursor(Qt.PointingHandCursor)
        close.setStyleSheet(
            "QPushButton{color:#9aa7b8;border:none;background:transparent;"
            "font-size:13px;} QPushButton:hover{color:#ff8080;}")
        close.clicked.connect(self.close)
        head.addWidget(close)
        root.addLayout(head)

        self.rank = QLabel("")
        self.rank.setStyleSheet("color:#ffcf7f;font-size:11px;")
        self.rank.setTextFormat(Qt.RichText)
        self.rank.setWordWrap(True)
        root.addWidget(self.rank)

        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(False)
        self.view.setFrameShape(QTextBrowser.NoFrame)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet(
            "background:transparent;border:none;color:#e8eef7;font-size:13px;")
        self.view.setFont(QFont("Noto Sans CJK SC", 10))
        self.view.setMouseTracking(True)
        self.view.viewport().setMouseTracking(True)
        self.view.setTextInteractionFlags(Qt.NoTextInteraction)
        self.view.setFocusPolicy(Qt.NoFocus)
        self.view.viewport().installEventFilter(self)
        self.view.installEventFilter(self)
        root.addWidget(self.view, 1)

        # 进场消息单独一块：小字、置灰、只留最近几条，不抢弹幕的地方
        self.enter_view = QTextBrowser()
        self.enter_view.setOpenExternalLinks(False)
        self.enter_view.setFrameShape(QTextBrowser.NoFrame)
        self.enter_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.enter_view.setStyleSheet(
            "background:transparent;border:none;color:#7d8a9c;font-size:11px;")
        self.enter_view.setFont(QFont("Noto Sans CJK SC", 8))
        self.enter_view.setTextInteractionFlags(Qt.NoTextInteraction)
        self.enter_view.setFocusPolicy(Qt.NoFocus)
        self.enter_view.setFixedHeight(ENTER_H)
        self.enter_view.viewport().installEventFilter(self)
        self.enter_view.installEventFilter(self)
        self.enter_view.hide()
        root.addWidget(self.enter_view, 0)

        self.input = QLineEdit()
        self.input.setPlaceholderText("发条弹幕…（回车发送）")
        self.input.setStyleSheet(
            "QLineEdit{background:rgba(255,255,255,18);border:1px solid #2c3140;"
            "border-radius:6px;color:#e8eef7;font-size:12px;padding:3px 6px;}"
            "QLineEdit:focus{border:1px solid #4a6fa5;}")
        self.input.returnPressed.connect(self.send_danmaku)
        root.addWidget(self.input, 0)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        self.status = QLabel("")
        self.status.setStyleSheet("color:#6f7c8f;font-size:11px;")
        bottom.addWidget(self.status, 1)
        root.addLayout(bottom)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 26), 1))
        p.setBrush(QBrush(QColor(18, 20, 26, 205)))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)

    # ---------- 事件 ----------
    def on_event(self, kind, data):
        if kind in ("status", "error", "room", "room_online"):
            log.info("%s %s", kind, data)
        if kind == "room":
            self.title.setText(data.get("title") or "直播间")
            self.live = data.get("live", 0)
            self.status.setText("直播中" if self.live else "未开播")
            if data.get("online"):
                self.count.setText("人气 %s" % self._fmt(data["online"]))
        elif kind == "status":
            self.status.setText(data.get("msg", ""))
            if data.get("msg") == "已连接":
                self.lines = [l for l in self.lines if "⚠" not in l]
                self.render()
        elif kind == "error":
            if not self.lines or "⚠" not in self.lines[-1]:
                self.add_line("#ff8f8f", "⚠ %s" % data.get("msg", ""))
            self.status.setText("连接异常，20 秒后重连")
            self.schedule_reconnect()
        elif kind == "danmaku":
            name = esc(data.get("user", ""))
            col = "#ff6b6b" if data.get("admin") else color_of(data.get("user"))
            self.add_line(col, name, self.emotes.render(data.get("text", "")))
        elif kind == "sent":
            if data.get("ok"):
                self.status.setText("已发送：%s" % data.get("text", ""))
            else:
                self.add_line("#ff8f8f", "⚠ 发送失败：%s" % esc(data.get("msg", "")))
        elif kind == "enter":
            self.add_enter("%s 进入直播间" % data.get("user", ""))
        elif kind == "rank":
            users = data.get("users") or []
            if users:
                self.rank.setText("在线榜：" + " · ".join(
                    "%d.%s" % (i, esc(u.get("name", "")))
                    for i, u in enumerate(users, 1)))
            else:
                self.rank.setText("")
        elif kind == "popularity":
            v = data.get("value", 0)
            if v > 1 and not self._online:
                self._online = v
                self.count.setText("人气 %s" % self._fmt(v))
        elif kind == "room_online":
            self._online = data.get("online", 0)
            self.live = data.get("live", self.live)
            self.count.setText("人气 %s" % self._fmt(self._online))
            if data.get("title"):
                self.title.setText(data["title"])
            if not self.live:
                self.status.setText("未开播")
        elif kind == "watched":
            self.watched = data.get("text", "")
            if self.watched:
                self.status.setText("%s · 看过 %s" % (
                    "直播中" if self.live else "未开播", self.watched))
            if self.watched:
                self.count.setText(self.watched)
        elif kind == "gift":
            self.add_line("#ffcf7f", "🎁 %s %s %s" % (
                esc(data.get("user", "")), esc(data.get("action", "")),
                esc(data.get("gift", ""))))

    def _fmt(self, n):
        n = int(n)
        return "%.1f万" % (n / 10000) if n >= 10000 else str(n)

    def add_line(self, color, *parts):
        if len(parts) == 2:
            html = ('<span style="color:%s">%s</span>：'
                    '<span style="color:#f2f6ff">%s</span>'
                    % (color, parts[0], parts[1]))
        else:
            html = '<span style="color:%s">%s</span>' % (color, parts[0])
        self.lines.append(html)
        if len(self.lines) > MAX_LINES:
            self.lines = self.lines[-MAX_LINES:]
        self.render()

    def render(self):
        body = "<br>".join(self.lines)
        self.view.setHtml(
            '<div style="line-height:150%%">%s</div>' % body)
        sb = self.view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def add_enter(self, text):
        self.enter_lines.append(
            '<span style="color:#7d8a9c">%s</span>' % esc(text))
        if len(self.enter_lines) > MAX_ENTER:
            self.enter_lines = self.enter_lines[-MAX_ENTER:]
        self.render_enter()

    def render_enter(self):
        if not (self._show_enter and self.enter_lines):
            self.enter_view.hide()
            return
        self.enter_view.show()
        self.enter_view.setHtml(
            '<div style="line-height:130%%">%s</div>'
            % "<br>".join(self.enter_lines))
        sb = self.enter_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def toggle_enter(self, on):
        self._show_enter = bool(on)
        self.render_enter()

    def send_danmaku(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        room = self.room

        def work():
            try:
                import bili
                s = bili.new_session()
                ok, msg = bili.send_danmaku(s, room, text)
            except Exception as e:
                ok, msg = False, str(e)
            self.bridge.event.emit("sent", {"ok": ok, "msg": msg, "text": text})

        threading.Thread(target=work, daemon=True).start()

    def schedule_reconnect(self):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(20000, self.reconnect)

    def reconnect(self):
        self.status.setText("正在重连…")
        try:
            self.client.stop()
        except Exception:
            pass
        self.client = DanmakuClient(self.room,
                                    lambda k, w: self.bridge.event.emit(k, w))
        self.client.start()

    def timerEvent(self, e):
        self._ticks = getattr(self, "_ticks", 0) + 1
        if self._ticks % 30 == 0:
            self.poll_online()

    def poll_online(self):
        """在线人数: 定时拉一次房间信息, 比心跳里的假人气靠谱"""
        import threading
        from bili import new_session, req

        def work():
            try:
                rid = getattr(self.client, "room_id", None) or self.room
                s = new_session()
                j = req(s, "https://api.live.bilibili.com/room/v1/Room/get_info",
                        {"room_id": rid}, tries=2)
                if j.get("code") == 0:
                    d = j["data"]
                    self.bridge.event.emit("room_online", {
                        "online": d.get("online", 0),
                        "live": d.get("live_status", 0),
                        "title": d.get("title", "")})
            except Exception as exc:
                log.info("拉在线人数失败: %s", exc)

        threading.Thread(target=work, daemon=True).start()

    # ---------- 拖动 / 右键 ----------
    def eventFilter(self, obj, ev):
        """让文字区也能拖动窗口"""
        if obj is self.view or obj is self.view.viewport():
            t = ev.type()
            if t == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                edges = self._resize_edges(ev.position().toPoint())
                if edges is not None and self._begin_resize(edges):
                    return True
                self._begin_move(ev)
                return True
            if t == QEvent.MouseButtonPress and ev.button() == Qt.RightButton:
                self.menu(ev.globalPosition().toPoint())
                return True
            if t == QEvent.MouseMove and not (ev.buttons() & Qt.LeftButton):
                e2 = self._resize_edges(ev.position().toPoint())
                if e2 == (Qt.RightEdge | Qt.BottomEdge):
                    self.setCursor(Qt.SizeFDiagCursor)
                elif e2 == Qt.RightEdge:
                    self.setCursor(Qt.SizeHorCursor)
                elif e2 == Qt.BottomEdge:
                    self.setCursor(Qt.SizeVerCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)
                return False
            if t == QEvent.MouseMove and (ev.buttons() & Qt.LeftButton):
                if self._drag:
                    self.move(ev.globalPosition().toPoint() - self._drag)
                return True
            if t == QEvent.MouseButtonDblClick:
                return True
            if t == QEvent.MouseButtonRelease:
                self._drag = None
                return True
            if t == QEvent.Wheel:
                return False
        return super().eventFilter(obj, ev)

    def _begin_move(self, ev):
        """Wayland 下必须交给合成器来移动"""
        wh = self.windowHandle()
        if wh is not None and wh.startSystemMove():
            self._drag = None
            return True
        self._drag = (ev.globalPosition().toPoint()
                      - self.frameGeometry().topLeft())
        return False

    EDGE = 6

    def _resize_edges(self, pos):
        r = pos.x() >= self.width() - self.EDGE
        b = pos.y() >= self.height() - self.EDGE
        if r and b:
            return Qt.RightEdge | Qt.BottomEdge
        if r:
            return Qt.RightEdge
        if b:
            return Qt.BottomEdge
        return None

    def _begin_resize(self, edges):
        wh = self.windowHandle()
        if wh is None or edges is None:
            return False
        self._drag = None          # 缩放时不要再被拖动逻辑带走
        return wh.startSystemResize(edges)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            edges = self._resize_edges(e.position().toPoint())
            if edges is not None and self._begin_resize(edges):
                return
            self._begin_move(e)
        elif e.button() == Qt.RightButton:
            self.menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._drag is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def wheelEvent(self, e):
        sb = self.view.verticalScrollBar()
        sb.setValue(sb.value() - e.angleDelta().y() // 2)

    def menu(self, pos):
        m = QMenu(self)
        m.setStyleSheet("QMenu{background:#1b1e26;color:#dfe6f2;"
                        "border:1px solid #2c3140;} QMenu::item:selected"
                        "{background:#2a3345;}")
        m.addAction("换个直播间…", self.change_room)
        m.addAction("填 / 改 cookie…", self.set_cookie)
        m.addAction("重新连接", self.reconnect)
        act = m.addAction("显示进场消息")
        act.setCheckable(True)
        act.setChecked(self._show_enter)
        act.toggled.connect(self.toggle_enter)
        m.addAction("清屏", lambda: (self.lines.clear(), self.enter_lines.clear(),
                                    self.render(), self.render_enter()))
        m.addSeparator()
        m.addAction("退出", self.close)
        m.exec(pos)

    def set_cookie(self):
        old = ""
        try:
            old = open(conf_path(), encoding="utf-8").read().strip()
        except Exception:
            pass
        text, ok = QInputDialog.getMultiLineText(
            self, "登录 cookie",
            "把浏览器里请求头那一整行 Cookie 粘进来\n"
            "（至少要含 SESSDATA）：", old)
        if not ok:
            self.show()
            self.raise_()
            return
        text = " ".join(text.split())
        with open(conf_path(), "w", encoding="utf-8") as f:
            f.write(text + "\n")
        self.lines.clear()
        self.reconnect()

    def change_room(self):
        r, ok = QInputDialog.getText(self, "换房间", "直播间号：", text=str(self.room))
        self.show()
        self.raise_()
        if ok and r.strip().isdigit():
            self.room = int(r.strip())
            self.lines.clear()
            self.render()
            self.reconnect()

    def closeEvent(self, e):
        try:
            self.client.stop()
        except Exception:
            pass
        from PySide6.QtWidgets import QApplication as _A
        e.accept()
        _A.quit()

    def _apply_place(self):
        g = QApplication.primaryScreen().availableGeometry()
        self.move(g.right() - self.width() - 40, g.top() + 60)


def main():
    setup_log()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if len(sys.argv) > 1 and sys.argv[1].strip().isdigit():
        room = int(sys.argv[1].strip())
    else:
        text, ok = QInputDialog.getText(None, "直播间号", "输入直播间号：")
        if not ok or not text.strip().isdigit():
            sys.exit(0)
        room = int(text.strip())

    w = DanmakuWindow(room)
    w.show()

    # Ctrl+C / SIGTERM 能真的退出
    import signal
    from PySide6.QtCore import QTimer

    state = {"stop": False}

    def _handler(signum, frame):
        state["stop"] = True

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)

    def _check():
        if state["stop"]:
            log.info("收到退出信号, 正在关闭")
            w.close()

    tick = QTimer()
    tick.timeout.connect(_check)
    tick.start(200)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
