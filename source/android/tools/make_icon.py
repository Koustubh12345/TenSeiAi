#!/usr/bin/env python3
"""Generate the TenSeiAi launcher icon (dark rounded square, green T)."""
import os
import struct
import sys
import zlib

SIZE = 144
SS = 3


def render():
    w = SIZE * SS
    px = [[(0x21, 0x21, 0x21, 0) for _ in range(w)] for _ in range(w)]
    r = 30 * SS
    for y in range(w):
        for x in range(w):
            dx = min(x, w - 1 - x)
            dy = min(y, w - 1 - y)
            inside = True
            if dx < r and dy < r:
                d2 = (r - dx) ** 2 + (r - dy) ** 2
                inside = d2 <= r * r
            if inside:
                px[y][x] = (0x10, 0xA3, 0x7F, 255)
    vx0, vx1 = (SIZE // 2 - 11) * SS, (SIZE // 2 + 11) * SS
    hy0, hy1 = 30 * SS, 52 * SS
    vy0, vy1 = 30 * SS, 114 * SS
    for y in range(hy0, vy1):
        for x in range(vx0, vx1):
            px[y][x] = (255, 255, 255, 255)
    for y in range(hy0, hy1):
        for x in range(34 * SS, 110 * SS):
            px[y][x] = (255, 255, 255, 255)
    out = bytearray()
    for y in range(SIZE):
        out.append(0)
        for x in range(SIZE):
            rr = gg = bb = aa = 0
            for sy in range(SS):
                for sx in range(SS):
                    p = px[y * SS + sy][x * SS + sx]
                    rr += p[0]
                    gg += p[1]
                    bb += p[2]
                    aa += p[3]
            n = SS * SS
            out += bytes((rr // n, gg // n, bb // n, aa // n))
    return bytes(out)


def png(raw, size):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "res/mipmap-xxhdpi/ic_launcher.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(png(render(), SIZE))
    print("icon written:", out)


if __name__ == "__main__":
    main()
