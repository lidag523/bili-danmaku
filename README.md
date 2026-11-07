> **Fully AI-generated (DeepSeek)**

# bili-danmaku

A floating window for Bilibili live chat, made for Linux (PySide6 + Qt6).

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
sudo pacman -U ./bili-danmaku-0.1.5.pkg.tar.zst
```

### Debian / Ubuntu

```bash
sudo apt install ./bili-danmaku-0.1.5.deb
```

### AppImage

```bash
chmod +x bili-danmaku-0.1.5.AppImage
./bili-danmaku-0.1.5.AppImage
```

### Run from source

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6 requests websocket-client brotli
.venv/bin/python main.py [room_id]
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
