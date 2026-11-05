"""极简 protobuf 解析: 只够读 B 站弹幕里的二进制消息"""


def _varint(buf, i):
    shift = 0
    val = 0
    while True:
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not b & 0x80:
            return val, i
        shift += 7


def fields(buf):
    """返回 [(field_no, value)], value 是 int 或 bytes"""
    out = []
    i = 0
    n = len(buf)
    while i < n:
        key, i = _varint(buf, i)
        fno, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(buf, i)
        elif wt == 2:
            ln, i = _varint(buf, i)
            v = buf[i:i + ln]
            i += ln
        elif wt == 5:
            v = buf[i:i + 4]
            i += 4
        elif wt == 1:
            v = buf[i:i + 8]
            i += 8
        else:
            break
        out.append((fno, v))
    return out


def decode_text(s):
    """JSON 里的二进制字段通常是 latin-1 转义过的字符串"""
    if isinstance(s, bytes):
        return s
    return s.encode("latin-1", "ignore")
