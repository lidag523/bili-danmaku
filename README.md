> **纯 AI 生成（DeepSeek）**

# bili-danmaku

B 站直播弹幕悬浮窗，给 Linux 用的（PySide6 + Qt6）。

## 功能

- 直播弹幕滚动显示
- 进场提示（谁进了直播间）
- 在线榜前三
- 人气值、累计看过人数
- 半透明悬浮窗，可拖动、可调大小，始终置顶
- 右键菜单：换房间 / 填 cookie / 重连 / 清屏 / 退出

## 安装

### Arch Linux

```bash
sudo pacman -U ./bili-danmaku-0.1.2.pkg.tar.zst
```

### Debian / Ubuntu

```bash
sudo apt install ./bili-danmaku-0.1.2.deb
```


### AppImage

```bash
chmod +x bili-danmaku-0.1.2.AppImage
./bili-danmaku-0.1.2.AppImage
```


### 源码运行

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6 requests websocket-client brotli
.venv/bin/python main.py [直播间号]
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


## 日志

```
~/.cache/bili-danmaku/app.log
```

## 已知限制

- B 站不提供真实在线观众名单，只能拿到「人气值」和累计「看过」；进场消息也只推一部分
- 没登录时进场消息会更少

## License

MIT
