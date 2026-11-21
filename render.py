"""Fiş içeriğini (blok listesi) 384 piksel genişliğinde siyah-beyaz görüntüye çevirir."""
import datetime
import os

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

WIDTH = 384
ROW_BYTES = WIDTH // 8
MARGIN = 4

# Yazıcı her bayttaki ilk pikseli en düşük bitte bekler.
LSB_FIRST = True

def _font_dirs():
    """Windows, macOS ve Linux'taki olağan yazı tipi klasörleri."""
    home = os.path.expanduser("~")
    return [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
        "/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts",
        os.path.join(home, "Library", "Fonts"),
        "/usr/share/fonts", "/usr/local/share/fonts",
        os.path.join(home, ".local", "share", "fonts"), os.path.join(home, ".fonts"),
    ]


# Her yazı tipi için (normal, kalın) dosya adı adayları, öncelik sırasıyla.
# Windows adları önce gelir; macOS'ta çoğu aynı ailenin farklı dosya adıdır;
# Linux'ta Microsoft yazı tipleri yoksa ölçüleri eşdeğer açık kaynak yazı tipleri kullanılır.
FONTS = {
    "Arial": (
        ["arial.ttf", "Arial.ttf", "LiberationSans-Regular.ttf", "Arimo-Regular.ttf", "DejaVuSans.ttf"],
        ["arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf", "Arimo-Bold.ttf", "DejaVuSans-Bold.ttf"],
    ),
    "Segoe UI": (
        ["segoeui.ttf", "SFNS.ttf", "Ubuntu-R.ttf", "NotoSans-Regular.ttf", "DejaVuSans.ttf"],
        ["segoeuib.ttf", "SFNS.ttf", "Ubuntu-B.ttf", "NotoSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
    ),
    "Times New Roman": (
        ["times.ttf", "Times New Roman.ttf", "LiberationSerif-Regular.ttf", "Tinos-Regular.ttf",
         "DejaVuSerif.ttf"],
        ["timesbd.ttf", "Times New Roman Bold.ttf", "LiberationSerif-Bold.ttf", "Tinos-Bold.ttf",
         "DejaVuSerif-Bold.ttf"],
    ),
    "Consolas": (
        ["consola.ttf", "Menlo.ttc", "LiberationMono-Regular.ttf", "DejaVuSansMono.ttf"],
        ["consolab.ttf", "Menlo.ttc", "LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"],
    ),
    "Comic Sans": (
        ["comic.ttf", "Comic Sans MS.ttf", "ComicNeue-Regular.ttf", "ComicNeue-Regular.otf", "DejaVuSans.ttf"],
        ["comicbd.ttf", "Comic Sans MS Bold.ttf", "ComicNeue-Bold.ttf", "ComicNeue-Bold.otf",
         "DejaVuSans-Bold.ttf"],
    ),
    "Impact": (
        ["impact.ttf", "Impact.ttf", "Anton-Regular.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
        ["impact.ttf", "Impact.ttf", "Anton-Regular.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
    ),
}

_font_index = None
_font_cache = {}


def _find_font_file(filename):
    """Yazı tipi klasörlerini (alt klasörler dahil) bir kez tarar, dosyayı adına göre bulur."""
    global _font_index
    if _font_index is None:
        _font_index = {}
        for d in _font_dirs():
            if not d or not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for f in files:
                    _font_index.setdefault(f.lower(), os.path.join(root, f))
    return _font_index.get(filename.lower())


def get_font(name, size, bold=False):
    key = (name, size, bold)
    if key not in _font_cache:
        candidates = FONTS.get(name, FONTS["Arial"])[1 if bold else 0]
        font = None
        for fn in candidates:
            path = _find_font_file(fn)
            if not path:
                continue
            try:
                font = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
        if font is None:
            font = ImageFont.load_default(size)
        _font_cache[key] = font
    return _font_cache[key]


def fill_placeholders(text):
    now = datetime.datetime.now()
    return text.replace("{tarih}", now.strftime("%d.%m.%Y")).replace("{saat}", now.strftime("%H:%M"))


def wrap_text(text, font, max_w):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for i, word in enumerate(para.split(" ")):
            cand = word if i == 0 else cur + " " + word   # baştaki boşluklar korunur
            if font.getlength(cand) <= max_w:
                cur = cand
                continue
            if cur:
                lines.append(cur)
            while word and font.getlength(word) > max_w:   # tek başına sığmayan uzun kelime
                i = len(word)
                while i > 1 and font.getlength(word[:i]) > max_w:
                    i -= 1
                lines.append(word[:i])
                word = word[i:]
            cur = word
        lines.append(cur)
    return lines


def _x_for(align, w):
    if align == "center":
        return (WIDTH - w) // 2
    if align == "right":
        return WIDTH - MARGIN - w
    return MARGIN


def render_text(b):
    font = get_font(b.get("font", "Arial"), int(b.get("size", 24)), bool(b.get("bold")))
    lines = wrap_text(fill_placeholders(b.get("text", "")), font, WIDTH - 2 * MARGIN)
    ascent, descent = font.getmetrics()
    lh = int((ascent + descent) * 1.08)
    img = Image.new("L", (WIDTH, max(1, lh * len(lines))), 255)
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((_x_for(b.get("align", "left"), int(font.getlength(line))), i * lh), line, font=font, fill=0)
    if b.get("invert"):
        img = ImageOps.invert(img)
    return img.point(lambda p: 0 if p < 150 else 255).convert("1", dither=Image.Dither.NONE)


def _error_block(msg):
    return render_text({"text": msg, "size": 18, "align": "center"})


def render_image(b):
    path = b.get("path", "")
    try:
        im = ImageOps.exif_transpose(Image.open(path))
    except Exception:
        return _error_block(f"[Fotoğraf açılamadı: {os.path.basename(path)}]")
    if im.mode in ("RGBA", "LA", "P", "PA"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, "white")
        bg.alpha_composite(im)
        im = bg
    im = im.convert("L")
    if b.get("orientation") == "landscape":
        # Yatay: fotoğraf 90° döndürülür, uzun kenarı fiş boyunca uzanır
        im = im.transpose(Image.Transpose.ROTATE_90)
    tw = max(8, int(WIDTH * int(b.get("width", 100)) / 100))
    th = max(1, round(im.height * tw / im.width))
    im = im.resize((tw, th), Image.Resampling.LANCZOS)
    im = ImageEnhance.Brightness(im).enhance(float(b.get("brightness", 1.0)))
    im = ImageEnhance.Contrast(im).enhance(float(b.get("contrast", 1.0)))
    dither = Image.Dither.FLOYDSTEINBERG if b.get("dither", True) else Image.Dither.NONE
    bw = im.convert("1", dither=dither)
    canvas = Image.new("1", (WIDTH, th), 1)
    canvas.paste(bw, (max(0, _x_for(b.get("align", "center"), tw)), 0))
    return canvas


def render_line(b):
    t = max(1, int(b.get("thickness", 2)))
    h = t + 12
    img = Image.new("1", (WIDTH, h), 1)
    d = ImageDraw.Draw(img)
    y0 = (h - t) // 2
    if b.get("style") == "dashed":
        x = MARGIN
        while x < WIDTH - MARGIN:
            d.rectangle([x, y0, min(x + 9, WIDTH - MARGIN), y0 + t - 1], fill=0)
            x += 16
    else:
        d.rectangle([MARGIN, y0, WIDTH - MARGIN, y0 + t - 1], fill=0)
    return img


def render_space(b):
    return Image.new("1", (WIDTH, max(1, int(b.get("height", 20)))), 1)


RENDERERS = {"text": render_text, "image": render_image, "line": render_line, "space": render_space}


def render(blocks):
    parts = []
    for b in blocks:
        fn = RENDERERS.get(b.get("type"))
        if fn:
            try:
                parts.append(fn(b))
            except Exception as e:
                parts.append(_error_block(f"[Hata: {e}]"))
    height = max(1, sum(p.height for p in parts))
    out = Image.new("1", (WIDTH, height), 1)
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height
    return out


# PIL '1' modu: MSB önce, 1 = beyaz. Yazıcı: 1 = siyah (ısıt), bit sırası LSB_FIRST'e göre.
_REV = [int(f"{i:08b}"[::-1], 2) for i in range(256)]
_TABLE = bytes((_REV[i ^ 0xFF] if LSB_FIRST else i ^ 0xFF) for i in range(256))


def to_rows(img):
    img = img.convert("1")
    if img.width != WIDTH:
        raise ValueError("Görüntü genişliği 384 olmalı")
    raw = img.tobytes().translate(_TABLE)
    return [raw[y * ROW_BYTES:(y + 1) * ROW_BYTES] for y in range(img.height)]
