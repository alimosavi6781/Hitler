# -*- coding: utf-8 -*-
"""Instagram sports poster (1080x1350) — navy/silver theme, Etehad Ilam U17 win."""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

W, H = 1080, 1350
F = "fonts/Vazirmatn-{}.ttf"

reshaper = arabic_reshaper.ArabicReshaper({'delete_harakat': False, 'support_ligatures': True})

def fa(text):
    return get_display(reshaper.reshape(text))

def font(weight, size):
    return ImageFont.truetype(F.format(weight), size)

# ---------- palette (team kit: navy / silver / ice blue) ----------
ICE    = (170, 215, 255)          # accent (was gold)
SILVER = (222, 232, 245)
WHITE  = (255, 255, 255)
GREY   = (205, 215, 230)
NAVY_T = (8, 18, 45, 205)         # translucent panel navy
GLOW_B = (60, 140, 255, 170)      # blue glow

# ---------- background ----------
bg = Image.open("bg_blue.png").convert("RGB")
bw, bh = bg.size
scale = max(W / bw, H / bh)
bg = bg.resize((int(bw * scale) + 1, int(bh * scale) + 1), Image.LANCZOS)
bw, bh = bg.size
bg = bg.crop(((bw - W) // 2, (bh - H) // 2, (bw - W) // 2 + W, (bh - H) // 2 + H))
bg = ImageEnhance.Contrast(bg).enhance(1.04)

img = bg.convert("RGBA")

# darken top & bottom for legibility
grad = Image.new("L", (1, H), 0)
for y in range(H):
    v = 0
    if y < 470:
        v = int(200 * (1 - y / 470) ** 1.25)
    if y > 950:
        v = max(v, int(205 * ((y - 950) / (H - 950)) ** 1.4))
    grad.putpixel((0, y), v)
shade = Image.new("RGBA", (W, H), (4, 8, 20, 255))
shade.putalpha(grad.resize((W, H)))
img = Image.alpha_composite(img, shade)

d = ImageDraw.Draw(img)

def text_center(y, txt, fnt, fill, glow=None):
    t = fa(txt)
    bbox = d.textbbox((0, 0), t, font=fnt)
    w = bbox[2] - bbox[0]
    x = (W - w) / 2
    if glow:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer)
        dl.text((x, y), t, font=fnt, fill=glow)
        layer = layer.filter(ImageFilter.GaussianBlur(14))
        img.alpha_composite(layer)
    d.text((x + 3, y + 4), t, font=fnt, fill=(0, 0, 0, 190))
    d.text((x, y), t, font=fnt, fill=fill)

def rounded(dr, box, r, **kw):
    dr.rounded_rectangle(box, radius=r, **kw)

# ---------- club logo, top center ----------
logo_h = 0
if os.path.exists("logo.png"):
    lg = Image.open("logo.png").convert("RGBA")
    lg.thumbnail((240, 205), Image.LANCZOS)
    # soft glow behind logo
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gx, gy = W // 2, 50 + lg.height // 2
    gd.ellipse((gx - 150, gy - 130, gx + 150, gy + 130), fill=(70, 130, 230, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    img.alpha_composite(glow)
    img.alpha_composite(lg, ((W - lg.width) // 2, 48))
    logo_h = lg.height
    d = ImageDraw.Draw(img)

# ---------- headline ----------
text_center(272, "برد شیرین نوجوانان اتحاد ایلام", font("FD-Black", 74), WHITE, glow=GLOW_B)
text_center(392, "مقابل تیم هاکان کرمانشاه", font("FD-Bold", 50), ICE)

# divider
d.line((W/2 - 170, 478, W/2 + 170, 478), fill=SILVER + (230,), width=3)
d.ellipse((W/2 - 7, 471, W/2 + 7, 485), fill=SILVER)

# ---------- ribbon: match info ----------
f_small = font("FD-SemiBold", 32)
t = fa("بازی دوستانه  |  چمن هوانیروز کرمانشاه")
bbox = d.textbbox((0, 0), t, font=f_small)
tw = bbox[2] - bbox[0]
pad = 26
ry = 510
box = ((W - tw) / 2 - pad, ry, (W + tw) / 2 + pad, ry + 58)
rounded(d, box, 29, fill=(12, 35, 85, 200), outline=SILVER + (220,), width=2)
d.text(((W - tw) / 2, ry + (58 - (bbox[3] - bbox[1])) / 2 - bbox[1]), t, font=f_small, fill=(225, 238, 255))

# ---------- team photos (auto-detected) ----------
import glob
photo_files = [p for p in ["team1.jpg", "team2.jpg"] if os.path.exists(p)]
if not photo_files:
    photo_files = sorted(glob.glob("/home/user/uploads/*.jpg"))[:2]
PHOTO_MODE = len(photo_files) >= 1

# ---------- score plate ----------
cx = 660
cy = 702 if PHOTO_MODE else 780
plate_w = 640
plate_h = 260 if PHOTO_MODE else 290
px0, py0 = cx - plate_w / 2, cy - plate_h / 2
plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dp = ImageDraw.Draw(plate)
rounded(dp, (px0, py0, px0 + plate_w, py0 + plate_h), 34, fill=NAVY_T, outline=SILVER + (210,), width=3)
img.alpha_composite(plate)
d = ImageDraw.Draw(img)

f_team = font("FD-Bold", 44)
f_score = ImageFont.truetype("fonts/Vazirmatn-Black.ttf", 108)

# team names under score (RTL: winner on right)
ty = py0 + plate_h - 88
t1 = fa("اتحاد ایلام")
t2 = fa("هاکان کرمانشاه")
b1 = d.textbbox((0, 0), t1, font=f_team)
b2 = d.textbbox((0, 0), t2, font=f_team)
x1 = px0 + plate_w - (b1[2] - b1[0]) - 48
x2 = px0 + 48
d.text((x1, ty), t1, font=f_team, fill=ICE)
d.text((x2, ty), t2, font=f_team, fill=GREY)

# compact Latin score centered — RTL pairing: winner's "1" on the right (above اتحاد)
parts = [("0", GREY), (" - ", (185, 200, 220)), ("1", ICE)]
total_w = sum(d.textlength(p, font=f_score) for p, _ in parts)
sb = d.textbbox((0, 0), "0 - 1", font=f_score)
sx = cx - total_w / 2
sy = py0 + (plate_h - 88 - (sb[3] - sb[1])) / 2 - sb[1] + 4
for p, col in parts:
    d.text((sx + 3, sy + 4), p, font=f_score, fill=(0, 0, 0, 200))
    d.text((sx, sy), p, font=f_score, fill=col)
    sx += d.textlength(p, font=f_score)

# ---------- description OR team photos ----------
if PHOTO_MODE:
    def framed_photo(path, size, angle):
        ph = Image.open(path).convert("RGB")
        tw_, th_ = size
        s = max(tw_ / ph.width, th_ / ph.height)
        ph = ph.resize((int(ph.width * s) + 1, int(ph.height * s) + 1), Image.LANCZOS)
        ph = ph.crop(((ph.width - tw_) // 2, (ph.height - th_) // 2,
                      (ph.width - tw_) // 2 + tw_, (ph.height - th_) // 2 + th_))
        card = Image.new("RGBA", (tw_ + 16, th_ + 16), (232, 240, 252, 255))
        card.paste(ph, (8, 8))
        card = card.rotate(angle, expand=True, resample=Image.BICUBIC)
        sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
        alpha = card.split()[3].point(lambda p: min(p, 170))
        sh.paste((0, 0, 0, 170), (0, 0), alpha)
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        return card, sh

    py = 862
    size = (470, 290)
    if len(photo_files) >= 2:
        specs = [(photo_files[0], 290, 2.5), (photo_files[1], 790, -2.5)]
    else:
        specs = [(photo_files[0], W // 2, 2.0)]
    for path, cx_p, ang in specs:
        card, sh = framed_photo(path, size, ang)
        pos = (int(cx_p - card.width / 2), py)
        img.alpha_composite(sh, (pos[0] + 6, pos[1] + 10))
        img.alpha_composite(card, pos)
    d = ImageDraw.Draw(img)
    slogan_y, sub_y = 1185, 1276
    slogan_size, sub_size = 62, 28
else:
    f_body = font("FD-Medium", 33)
    lines = [
        "نوجوانان اتحاد در یک نمایش هماهنگ و تاکتیکی،",
        "با یک گل تیم خوب هاکان را شکست دادند.",
    ]
    y = 995
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    db_ = ImageDraw.Draw(band)
    maxw = 0
    for ln in lines:
        b = d.textbbox((0, 0), fa(ln), font=f_body)
        maxw = max(maxw, b[2] - b[0])
    rounded(db_, ((W - maxw) / 2 - 34, y - 16, (W + maxw) / 2 + 34, y + 52 * len(lines) + 10), 22,
            fill=(5, 12, 30, 155))
    band = band.filter(ImageFilter.GaussianBlur(1))
    img.alpha_composite(band)
    d = ImageDraw.Draw(img)
    for ln in lines:
        t = fa(ln)
        b = d.textbbox((0, 0), t, font=f_body)
        x = (W - (b[2] - b[0])) / 2
        d.text((x + 2, y + 2), t, font=f_body, fill=(0, 0, 0, 190))
        d.text((x, y), t, font=f_body, fill=GREY)
        y += 52
    slogan_y, sub_y = 1128, 1244
    slogan_size, sub_size = 72, 33

# ---------- slogan ----------
text_center(slogan_y, "آینده ساختنی است", font("FD-Black", slogan_size), ICE, glow=(90, 160, 255, 180))
text_center(sub_y, "این پیروزی، قدمی از هزار قدمِ مسیر ماست",
            font("FD-Medium", sub_size), (235, 242, 252))

# thin silver frame
fr = ImageDraw.Draw(img)
fr.rectangle((26, 26, W - 26, H - 26), outline=(210, 225, 245, 140), width=2)

img.convert("RGB").save("poster_final.jpg", quality=93)
print("saved poster_final.jpg")
