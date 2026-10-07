#!/usr/bin/env python3
"""
サムネイル用アイコンを作るスクリプト（追加インストール不要・Python標準機能だけ）

使い方（Narostudio フォルダで実行）:
    python3 tools/make_icon.py cd   images/915_cd.png 7FC786   ← BGM・歌モノ用のCD
    python3 tools/make_icon.py note images/a27_n.png  7FC786   ← ジングル用の音符

色は6桁のカラーコード（#は付けても付けなくてもOK）。
どちらも 800x800 で、既存のアイコンと同じ寸法・同じ形になります。
音符は既存のアイコンから形を借りてくるので、images/ の中に音符アイコンが
1つ以上残っている必要があります。
"""
import os
import struct
import sys
import zlib

SIZE = 800
C = SIZE / 2.0
R_DISC, R_RING, R_HOLE, R_CORE = 250.0, 105.0, 70.0, 45.0  # CDの各半径
SS = 3  # 輪郭をなめらかにするための分割数


# ---------- PNGの読み書き ----------
def read_png(path):
    data = open(path, "rb").read()
    pos, idat, ihdr = 8, b"", None
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + ln
    w, h, depth, ctype = ihdr[0], ihdr[1], ihdr[2], ihdr[3]
    if depth != 8 or ctype not in (2, 6):
        raise SystemExit(f"未対応のPNG形式です（depth={depth} color={ctype}）: {path}")
    ch = 3 if ctype == 2 else 4
    raw = zlib.decompress(idat)

    rows, prev, pos = [], bytearray(w * ch), 0
    for _ in range(h):
        f = raw[pos]; pos += 1
        line = bytearray(raw[pos:pos + w * ch]); pos += w * ch
        for i in range(len(line)):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        rows.append(line); prev = line
    return w, h, ch, rows


def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    out += chunk(b"IDAT", zlib.compress(raw, 9))
    out += chunk(b"IEND", b"")
    open(path, "wb").write(out)
    print("作成:", path, f"({len(out):,} bytes)")


# ---------- CDアイコン ----------
def make_cd(path, bg):
    rows = []
    for y in range(SIZE):
        row = bytearray()
        for x in range(SIZE):
            white = 0
            for sy in range(SS):
                for sx in range(SS):
                    px = x + (sx + 0.5) / SS - C
                    py = y + (sy + 0.5) / SS - C
                    d = (px * px + py * py) ** 0.5
                    # 中心から外へ：色 → 白 → 色のリング → 白い盤面 → 背景色
                    if (R_CORE < d <= R_HOLE) or (R_RING < d <= R_DISC):
                        white += 1
            a = white / (SS * SS)
            row += bytes(round(255 * a + bg[i] * (1 - a)) for i in range(3))
        rows.append(row)
    write_png(path, SIZE, SIZE, rows)


# ---------- 音符アイコン（既存の形を借りて色だけ差し替え） ----------
def find_note_template(outdir):
    # 出力先と、リポジトリの images/ の両方から見本を探す
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (outdir or ".", os.path.join(here, "..", "images"), "images"):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith("_n.png"):
                return os.path.join(d, f)
    raise SystemExit("音符アイコンの見本が images/ に見つかりません")


def make_note(path, bg):
    src = find_note_template(os.path.dirname(path))
    print("見本:", src)
    w, h, ch, rows = read_png(src)
    oldbg = tuple(rows[0][0:3])
    span = [255 - oldbg[i] for i in range(3)]
    out = []
    for r in rows:
        nr = bytearray()
        for x in range(w):
            px = r[x * ch:x * ch + 3]
            # 元の背景色 → 白 のどれくらい白寄りかを測る
            vals = [(px[i] - oldbg[i]) / span[i] for i in range(3) if span[i] > 8]
            a = min(1.0, max(0.0, sum(vals) / len(vals))) if vals else 0.0
            nr += bytes(round(255 * a + bg[i] * (1 - a)) for i in range(3))
        out.append(nr)
    write_png(path, w, h, out)


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ("cd", "note"):
        raise SystemExit(__doc__)
    kind, dst, color = sys.argv[1], sys.argv[2], sys.argv[3].lstrip("#")
    if len(color) != 6:
        raise SystemExit("色は6桁のカラーコードで指定してください（例 7FC786）")
    rgb = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    (make_cd if kind == "cd" else make_note)(dst, rgb)
