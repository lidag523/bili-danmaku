# Maintainer: Lavalucky <you@example.com>
pkgname=bili-danmaku
pkgver=0.1.0
pkgrel=18
pkgdesc="B站直播弹幕悬浮窗 (弹幕/进场/在线人数)"
arch=('any')
url="https://live.bilibili.com/"
license=('MIT')
depends=('python' 'pyside6' 'python-requests' 'python-websocket-client' 'python-brotli')
options=('!strip')
source=("main.py" "danmaku.py" "bili.py" "pb.py" "bili-danmaku.sh")
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP')

prepare() {
  cd "$srcdir"
  :
}

package() {
  install -d "$pkgdir/usr/lib/bili-danmaku"
  install -m644 "$srcdir/main.py" "$srcdir/danmaku.py" "$srcdir/bili.py" \
    "$srcdir/pb.py" "$pkgdir/usr/lib/bili-danmaku/"
  install -Dm755 "$srcdir/bili-danmaku.sh" "$pkgdir/usr/bin/bili-danmaku"
  install -Dm644 /dev/stdin "$pkgdir/usr/share/doc/$pkgname/README.md" <<'DOC'
# bili-danmaku

B 站直播弹幕悬浮窗。

用法:
    bili-danmaku [直播间号]

不填会弹窗让你输房间号。窗口内右键可以换房间、重连、清屏。

想显示完整用户名需要登录 cookie, 放到:
    ~/.config/bili-danmaku/cookie.txt
里面写一行 SESSDATA=xxx; 或者整行浏览器 cookie 串。
DOC
}
