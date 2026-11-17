"""Draw the application icon and save it as PNG, ICO (Windows) and ICNS (macOS).

    python tools/make_icon.py

Only the standard library is used. The three files in assets/ are already in the project,
so you only need to run this again if you change the drawing.
"""

import os
import struct
import zlib

SIZE = 256
BACKGROUND = (37, 99, 201)                                   # the blue of the Start button
BARS = [(78, 121, 167), (242, 142, 43), (89, 161, 79), (225, 87, 89)]    # four process colours
WHITE = (255, 255, 255)


def draw():
    """The picture: a rounded blue square with a small Gantt chart. Returns rows of (r, g, b, a) pixels."""
    rows = []
    radius = 48
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            # rounded corners: outside the corner circle the pixel is transparent
            cx = min(max(x, radius), SIZE - 1 - radius)
            cy = min(max(y, radius), SIZE - 1 - radius)
            inside = (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2
            color = BACKGROUND
            if 44 <= x < 212:
                if 58 <= y < 98:                             # the top bar: four processes take turns
                    color = BARS[(x - 44) // 42]
                elif 112 <= y < 152 and x < 44 + 126:        # two more bars, like a queue getting shorter
                    color = WHITE
                elif 166 <= y < 206 and x < 44 + 84:
                    color = WHITE
            row.append(color + (255,) if inside else (0, 0, 0, 0))
        rows.append(row)
    return rows


def png_bytes(rows):
    """Encode RGBA pixel rows as a PNG file."""
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    raw = b"".join(b"\x00" + bytes(value for pixel in row for value in pixel) for row in rows)
    header = struct.pack(">IIBBBBB", len(rows[0]), len(rows), 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def main():
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(folder, exist_ok=True)
    png = png_bytes(draw())
    with open(os.path.join(folder, "icon.png"), "wb") as file:
        file.write(png)
    with open(os.path.join(folder, "icon.ico"), "wb") as file:      # an ICO file may simply contain a PNG
        file.write(struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22) + png)
    with open(os.path.join(folder, "icon.icns"), "wb") as file:     # so may an ICNS file ("ic08" = 256 x 256)
        file.write(b"icns" + struct.pack(">I", 16 + len(png)) + b"ic08" + struct.pack(">I", 8 + len(png)) + png)
    print("Wrote icon.png, icon.ico and icon.icns in", folder)


if __name__ == "__main__":
    main()
