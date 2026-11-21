# bili-danmaku

[中文](#中文) · [English](#english)

> **纯 AI 生成（DeepSeek）**

## 中文

B 站直播弹幕悬浮窗，给 Linux 用的（PySide6 + Qt6）。

![截图](docs/images/preview/screenshot.png)

## 功能

- 直播弹幕滚动显示
- 进场提示（谁进了直播间）
- 在线榜前三
- 人气值、累计看过人数
- 半透明悬浮窗，可拖动、可调大小，始终置顶
- 右键菜单：换房间 / 填 cookie / 重连 / 语言 / 清屏 / 退出
- 发送弹幕和表情
- 界面按系统语言自动中英文切换，也可右键手动选

## 安装

### Arch Linux

```bash
sudo pacman -U ./bili-danmaku-0.1.8.pkg.tar.zst
```

### Debian / Ubuntu

```bash
sudo apt install ./bili-danmaku-0.1.8.deb
```


### AppImage

```bash
chmod +x bili-danmaku-0.1.8.AppImage
./bili-danmaku-0.1.8.AppImage
```


### 源码运行

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6 requests websocket-client brotli
.venv/bin/python main.py [直播间号]
```

### 用 uv 运行（不建虚拟环境）

本机装了 [uv](https://docs.astral.sh/uv/) 的话，可以一行起，依赖由 uv 自己拉、自己缓存：

```bash
uv run --with PySide6 --with requests --with websocket-client --with brotli \
  main.py [直播间号]
```

第一次会下载依赖（PySide6 体积较大），之后走缓存，秒起。

想复用系统里已经装好的 PySide6，就换成：

```bash
uv venv --system-site-packages .venv
uv run main.py [直播间号]
```

## 用法

```bash
bili-danmaku [直播间号]
```


窗口上：

- 左键按住拖动
- 右边直拖改宽，下边改高，右下角两个一起改
- 右键出菜单

## 登录 cookie（可选）

不登录也能看弹幕，只是用户名会被 B 站打码成 `X***` 这样。

右键 → 「填 / 改 cookie…」，把浏览器请求头里那一整行 Cookie 粘进去（至少要含 `SESSDATA`）。存在：

```
~/.config/bili-danmaku/cookie.txt
```

也可以用环境变量 `BILI_DANMAKU_COOKIE` 指到别的文件。


## 语言

界面默认跟随系统语言：看 `BILI_DANMAKU_LANG`、`LC_ALL`、`LC_MESSAGES`、`LANG`，
是 `zh*` 就中文，否则英文。也可以右键菜单「语言 / Language」手动切换，选择记在：

```
~/.config/bili-danmaku/lang.txt
```

## 作者与贡献

- 初始版本与最早几个提交：Lavalucky（[@LuckyLava](https://github.com/LuckyLava)）
- 维护：lidag523

> 说明：早期整理提交历史时执行过一次 `filter-branch`，把最早 3 个提交的作者信息一并改写成了维护者身份，
> 原始署名因此没有保留下来。这里补记一下，感谢最初的实现。

## 日志

```
~/.cache/bili-danmaku/app.log
```

## 已知限制

- B 站不提供真实在线观众名单，只能拿到「人气值」和累计「看过」；进场消息也只推一部分
- 没登录时进场消息会更少

## License

MIT

---

> **Fully AI-generated (DeepSeek)**

## English

A floating window for Bilibili live chat, made for Linux (PySide6 + Qt6).

![Screenshot](docs/images/preview/screenshot.png)

## Features

- Scrolling live chat (danmaku)
- Entry notices (who joined the room)
- Top 3 of the online ranking
- Popularity value and total viewers
- Translucent always-on-top window, draggable and resizable
- Right-click menu: change room / set cookie / reconnect / language / clear / quit
- Send comments and emotes
- UI follows the system language, or pick one from the right-click menu

## Install

### Arch Linux

```bash
sudo pacman -U ./bili-danmaku-0.1.8.pkg.tar.zst
```

### Debian / Ubuntu

```bash
sudo apt install ./bili-danmaku-0.1.8.deb
```

### AppImage

```bash
chmod +x bili-danmaku-0.1.8.AppImage
./bili-danmaku-0.1.8.AppImage
```

### Run from source

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6 requests websocket-client brotli
.venv/bin/python main.py [room_id]
```

### Run with uv (no manual venv)

If you have [uv](https://docs.astral.sh/uv/) installed, a single command pulls and
caches the dependencies for you:

```bash
uv run --with PySide6 --with requests --with websocket-client --with brotli \
  main.py [room_id]
```

The first run downloads the dependencies (PySide6 is large); later runs are
instant thanks to uv's cache.

To reuse the PySide6 already installed on your system instead:

```bash
uv venv --system-site-packages .venv
uv run main.py [room_id]
```

## Usage

```bash
bili-danmaku [room_id]
```

In the window:

- Hold the left button to drag it around
- Drag the right edge to change the width, the bottom edge to change the
  height, or the bottom-right corner to change both
- Right-click for the menu

## Login cookie (optional)

You can read chat without logging in, but Bilibili masks usernames as
`X***`.

Right-click → "Set / change cookie…" and paste the whole `Cookie` header line
from your browser (it must contain `SESSDATA`). It is stored in:

```
~/.config/bili-danmaku/cookie.txt
```

You can also point `BILI_DANMAKU_COOKIE` at a different file.

## Language

The UI is in English unless the system locale is Chinese (`zh*`), checked in
this order: `BILI_DANMAKU_LANG`, `LC_ALL`, `LC_MESSAGES`, `LANG`. You can also
switch it from the right-click menu ("语言 / Language"); the choice is saved to:

```
~/.config/bili-danmaku/lang.txt
```

## Credits

- Initial version and the earliest commits: Lavalucky ([@LuckyLava](https://github.com/LuckyLava))
- Maintainer: lidag523

> Note: an early `filter-branch` history rewrite overwrote the authorship of the first three
> commits with the maintainer's identity, so the original attribution was lost. Recording it
> here to give credit where it is due.

## Logs

```
~/.cache/bili-danmaku/app.log
```

## Known limitations

- Bilibili does not expose the real list of online viewers. Only the
  popularity value and the cumulative viewer count are available, and only
  some entry messages are pushed
- Entry messages get even sparser when you are not logged in

## License

MIT
