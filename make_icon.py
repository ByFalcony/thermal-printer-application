"""Uygulama simgesini (icon.ico ve icon.png) üretir. Bir kez çalıştırmak yeterli."""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
S = 1024  # yüksek çözünürlükte çizip küçült


def draw():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # mavi zemin (degrade)
    bg = Image.new("RGBA", (S, S))
    bd = ImageDraw.Draw(bg)
    top, bot = (59, 130, 246), (29, 78, 216)
    for y in range(S):
        t = y / (S - 1)
        bd.line([(0, y), (S, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([40, 40, S - 40, S - 40], radius=220, fill=255)
    img.paste(bg, (0, 0), mask)

    # fiş kağıdı (alt kenarı tırtıklı)
    x0, x1, y0, y1 = 270, S - 270, 190, 790
    tooth = (x1 - x0) / 8
    pts = [(x0, y0), (x1, y0), (x1, y1)]
    x, down = x1, True
    while x > x0 + 1:
        x -= tooth / 2
        pts.append((x, y1 + (55 if down else 0)))
        down = not down
    pts.append((x0, y1))
    shadow = [(px + 18, py + 24) for px, py in pts]
    d.polygon(shadow, fill=(15, 40, 120, 110))
    d.polygon(pts, fill=(255, 255, 255, 255))

    # fiş üzerindeki satırlar
    ink = (30, 58, 138, 255)
    d.rounded_rectangle([x0 + 70, 270, x1 - 70, 330], radius=30, fill=ink)          # başlık
    for i, w in enumerate([1.0, 0.75, 0.9]):
        y = 400 + i * 80
        d.rounded_rectangle([x0 + 70, y, x0 + 70 + (x1 - x0 - 140) * w, y + 34], radius=17,
                            fill=(148, 163, 184, 255))
    # kesikli çizgi
    x = x0 + 70
    while x < x1 - 70:
        d.rectangle([x, 652, min(x + 36, x1 - 70), 668], fill=ink)
        x += 60
    return img


def main():
    img = draw()
    img.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(HERE, "icon.png"))
    img.save(os.path.join(HERE, "icon.ico"),
             sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icon.ico ve icon.png oluşturuldu")


if __name__ == "__main__":
    main()
