#!/usr/bin/env python3
"""AIFLOWED renderer: turns a JSON spec into carousel slides (JPEG) + a silent Reel (MP4) + cover.

Usage:
  python render.py spec.json OUT_DIR                  # renders whatever is in the spec
  python render.py spec.json OUT_DIR --only carousel  # or: --only reel

Outputs:
  OUT_DIR/posts/slide_01.jpg ... (1080x1350)
  OUT_DIR/reels/reel.mp4 + cover.jpg (1080x1920, 30 fps, silent)

See references/spec-format.md for the spec. Prints WARNING lines when text risks overflowing.
Requires: Pillow, ffmpeg, Poppins fonts (searched in common locations).
"""
import json, os, subprocess, sys, glob, shutil, tempfile
from PIL import Image, ImageDraw, ImageFont

DG = "#0B3D2E"; MINT = "#A8E6CF"; LM = "#E8FBF3"; AG = "#2ECC8F"; RED = "#E5484D"; PINK = "#FDECEC"
HANDLE_DEFAULT = "@aiflowed"
WARN = []


def font_path(weight):
    name = f"Poppins-{weight}.ttf"
    roots = ["/usr/share/fonts/truetype/google-fonts/", "/usr/share/fonts/truetype/poppins/",
             "/usr/share/fonts/", "/Library/Fonts/", os.path.expanduser("~/Library/Fonts/"),
             os.path.expanduser("~/.fonts/"), "C:/Windows/Fonts/"]
    for r in roots:
        hits = glob.glob(os.path.join(r, "**", name), recursive=True)
        if hits:
            return hits[0]
    raise SystemExit(f"Poppins {weight} not found. Install Poppins (Google Fonts) or edit font_path() in render.py.")


_cache = {}
def F(weight, size):
    k = (weight, size)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(font_path(weight), size)
    return _cache[k]


def wrap(d, text, font, maxw):
    lines = []
    for block in str(text).split("\n"):
        cur = ""
        for w in block.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= maxw:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def para(d, xy, text, font, fill, maxw, lh=1.28):
    x, y = xy
    for ln in wrap(d, text, font, maxw):
        d.text((x, y), ln, font=font, fill=fill)
        y += int(font.size * lh)
    return y


def height(d, text, font, maxw, lh=1.28):
    return len(wrap(d, text, font, maxw)) * int(font.size * lh)


def check(d, x, y, s, col, w=14):
    d.line((x, y + s * 0.55, x + s * 0.35, y + s * 0.9), fill=col, width=w, joint="curve")
    d.line((x + s * 0.35, y + s * 0.9, x + s, y + s * 0.1), fill=col, width=w, joint="curve")


def cross(d, x, y, s, col, w=14):
    d.line((x, y, x + s, y + s), fill=col, width=w)
    d.line((x + s, y, x, y + s), fill=col, width=w)


def num_circle(d, x, y, r, n):
    d.ellipse((x, y, x + 2 * r, y + 2 * r), fill=AG)
    f = F("Bold", int(r * 1.45))
    w = d.textlength(str(n), font=f)
    d.text((x + r - w / 2, y + r - f.size * 0.68), str(n), font=f, fill=DG)


def guard(label, bottom, limit):
    if bottom > limit:
        WARN.append(f"{label}: content ends at y={bottom}, limit {limit}. Shorten the text.")


# ---------------- CAROUSEL (1080x1350) ----------------
W, H = 1080, 1350
M = 82


def c_new(bg):
    im = Image.new("RGB", (W, H), bg)
    return im, ImageDraw.Draw(im)


def c_footer(d, i, n, dark, handle):
    c = MINT if dark else DG
    f = F("Medium", 30)
    d.text((M, H - 135), handle, font=f, fill=c)
    t = f"{i}/{n}"
    d.text((W - M - d.textlength(t, font=f), H - 135), t, font=f, fill=c)


def s_hook(s, i, n, handle):
    im, d = c_new(DG)
    d.text((M, 110), s.get("kicker", "AIFLOWED"), font=F("Bold", 34), fill=AG)
    y = para(d, (M, 300), s["headline"], F("Bold", 92), MINT, W - 2 * M, 1.18)
    if s.get("badge"):
        d.ellipse((M, y + 50, M + 110, y + 160), fill=AG)
        f = F("Bold", 72)
        d.text((M + 55 - d.textlength(str(s["badge"]), font=f) / 2, y + 60), str(s["badge"]), font=f, fill=DG)
        d.text((M + 140, y + 78), s.get("badge_text", ""), font=F("Regular", 44), fill=LM)
        y += 160
    guard(f"slide {i} hook", y, H - 200)
    c_footer(d, i, n, True, handle)
    return im


def s_mistake(s, i, n, handle):
    im, d = c_new(LM)
    d.text((M, 110), s.get("label", "THE MISTAKE"), font=F("Bold", 30), fill=RED)
    wsub = s.get("wrong_sub", "")
    top = 190
    tl = height(d, s["wrong"], F("Bold", 56), W - 2 * M - 190, 1.15)
    sub_off = max(48 + tl, 150) + 10
    hb = (sub_off + height(d, wsub, F("Regular", 38), W - 2 * M - 80) + 45) if wsub else (48 + tl + 50)
    d.rounded_rectangle((M, top, W - M, top + hb), radius=36, fill=PINK, outline=RED, width=4)
    cross(d, M + 40, top + 60, 70, RED, 14)
    yy = para(d, (M + 150, top + 48), s["wrong"], F("Bold", 56), DG, W - 2 * M - 190, 1.15)
    if wsub:
        para(d, (M + 40, top + sub_off), wsub, F("Regular", 38), DG, W - 2 * M - 80)
    t2 = top + hb + 80
    right = s["right"]
    rsub = s.get("right_sub", "")
    rl = len(wrap(d, right, F("Bold", 56), W - 2 * M - 190))
    hb2 = 90 + rl * 64 + (height(d, rsub, F("Regular", 38), W - 2 * M - 80) + 40 if rsub else 30)
    d.rounded_rectangle((M, t2, W - M, t2 + hb2), radius=36, fill=DG)
    check(d, M + 40, t2 + 52, 76, AG, 16)
    yy = para(d, (M + 150, t2 + 44), right, F("Bold", 56), MINT, W - 2 * M - 190, 1.15)
    if rsub:
        para(d, (M + 40, yy + 30), rsub, F("Regular", 38), LM, W - 2 * M - 80)
    guard(f"slide {i} mistake", t2 + hb2, H - 200)
    c_footer(d, i, n, False, handle)
    return im


def s_step(s, i, n, handle):
    im, d = c_new(LM)
    num_circle(d, M, 92, 44, s.get("number", i - 2))
    d.text((200, 120), s.get("label", ""), font=F("Medium", 36), fill=DG)
    y = para(d, (M, 250), s["title"], F("Bold", 100), DG, W - 2 * M, 1.1)
    if s.get("sub"):
        y = para(d, (M, y + 20), s["sub"], F("Regular", 44), DG, W - 2 * M)
    ctop = max(y + 70, 600)
    ft = F("Medium", 44)
    ch = height(d, s["card"], ft, W - 2 * M - 90, 1.3)
    cb = ctop + 60 + 60 + ch + 60
    d.rounded_rectangle((M, ctop, W - M, cb), radius=36, fill=DG)
    d.text((M + 44, ctop + 44), s.get("card_label", "PROMPT"), font=F("Medium", 28), fill=AG)
    para(d, (M + 44, ctop + 104), s["card"], ft, MINT, W - 2 * M - 90, 1.3)
    if s.get("note"):
        cb = para(d, (M, cb + 36), s["note"], F("Medium", 30), DG, W - 2 * M, 1.3)
    guard(f"slide {i} step", cb, H - 190)
    c_footer(d, i, n, False, handle)
    return im


def s_list(s, i, n, handle):
    im, d = c_new(LM)
    y = para(d, (M, 140), s["title"], F("Bold", 84), DG, W - 2 * M, 1.12) + 30
    for it in s["items"]:
        h = height(d, it, F("Medium", 40), W - 2 * M - 150, 1.25)
        hh = max(130, h + 60)
        d.rounded_rectangle((M, y, W - M, y + hh), radius=30, fill=DG)
        check(d, M + 36, y + hh / 2 - 30, 60, AG, 13)
        para(d, (M + 130, y + (hh - h) / 2), it, F("Medium", 40), MINT, W - 2 * M - 150, 1.25)
        y += hh + 24
    guard(f"slide {i} list", y, H - 190)
    c_footer(d, i, n, False, handle)
    return im


def s_cta(s, i, n, handle):
    im, d = c_new(DG)
    y = para(d, (M, 330), s["headline"], F("Bold", 100), MINT, W - 2 * M, 1.15)
    d.rounded_rectangle((M, y + 60, W - M, y + 210), radius=75, fill=AG)
    f = F("Bold", 52)
    t = s.get("button", "Follow " + handle)
    d.text((W / 2 - d.textlength(t, font=f) / 2, y + 98), t, font=f, fill=DG)
    if s.get("sub"):
        para(d, (M, y + 270), s["sub"], F("Regular", 38), LM, W - 2 * M)
    guard(f"slide {i} cta", y + 330, H - 190)
    c_footer(d, i, n, True, handle)
    return im


SLIDE = {"hook": s_hook, "mistake": s_mistake, "step": s_step, "list": s_list, "cta": s_cta}


def render_carousel(spec, out):
    os.makedirs(out, exist_ok=True)
    slides = spec["slides"]
    handle = spec.get("handle", HANDLE_DEFAULT)
    if not 2 <= len(slides) <= 10:
        WARN.append("Carousel needs 2-10 slides (5-8 recommended).")
    for i, s in enumerate(slides, 1):
        SLIDE[s["type"]](s, i, len(slides), handle).save(os.path.join(out, f"slide_{i:02d}.jpg"), quality=95)
    print(f"carousel: {len(slides)} slides -> {out}")


# ---------------- REEL (1080x1920) ----------------
RW, RH = 1080, 1920


def r_new(bg):
    im = Image.new("RGB", (RW, RH), bg)
    return im, ImageDraw.Draw(im)


def r_foot(d, dark, handle):
    d.text((M, RH - 260), handle, font=F("Medium", 34), fill=MINT if dark else DG)


def r_hook(s, h):
    im, d = r_new(DG)
    y = para(d, (M, 560), s["headline"], F("Bold", 110), MINT, RW - 2 * M, 1.15)
    if s.get("sub"):
        y = para(d, (M, y + 50), s["sub"], F("Bold", 70), AG, RW - 2 * M)
    guard("reel hook", y, RH - 300)
    r_foot(d, True, h)
    return [(im, s.get("seconds", 3))]


def r_mistake(s, h):
    im, d = r_new(LM)
    if s.get("label"):
        d.text((M, 420), s["label"], font=F("Medium", 32), fill=DG)
    sub = s.get("sub", "")
    ht = len(wrap(d, s["wrong"], F("Bold", 58), RW - 330)) * 70
    hb = 130 + ht + (height(d, sub, F("Regular", 42), RW - 2 * M - 88) + 30 if sub else 0)
    d.rounded_rectangle((M, 540, RW - M, 540 + hb), radius=40, fill=PINK, outline=RED, width=4)
    cross(d, M + 44, 610, 76, RED, 15)
    y = para(d, (M + 160, 596), s["wrong"], F("Bold", 58), DG, RW - 330, 1.2)
    if sub:
        para(d, (M + 44, max(y, 720) + 20), sub, F("Regular", 42), DG, RW - 2 * M - 88)
    r_foot(d, False, h)
    return [(im, s.get("seconds", 5))]


def r_prompt(s, h):
    words = s["text"].split()
    steps = s.get("steps", 6)
    per = s.get("seconds", 12) / steps
    out = []
    for k in range(1, steps + 1):
        n = int(len(words) * k / steps) if k < steps else len(words)
        im, d = r_new(LM)
        d.text((M, 300), s.get("title", "THE PROMPT"), font=F("Bold", 36), fill=DG)
        ft = F("Medium", 50)
        full = height(d, s["text"], ft, RW - 2 * M - 100, 1.32)
        d.rounded_rectangle((M, 400, RW - M, 400 + 170 + full + 60), radius=44, fill=DG)
        d.text((M + 48, 460), s.get("label", "COPY THIS"), font=F("Medium", 30), fill=AG)
        para(d, (M + 48, 540), " ".join(words[:n]), ft, MINT, RW - 2 * M - 100, 1.32)
        guard("reel prompt", 400 + 170 + full + 60, RH - 300)
        r_foot(d, False, h)
        out.append((im, per))
    return out


def r_checklist(s, h):
    im, d = r_new(DG)
    d.text((M, 380), s.get("title", "What you get"), font=F("Bold", 64), fill=MINT)
    y = 560
    for t in s["items"]:
        lh = len(wrap(d, t, F("Bold", 54), RW - 2 * M - 190))
        hh = max(160, lh * 66 + 70)
        d.rounded_rectangle((M, y, RW - M, y + hh), radius=36, fill=LM)
        check(d, M + 44, y + hh / 2 - 38, 76, AG, 16)
        para(d, (M + 170, y + (hh - lh * 66) / 2), t, F("Bold", 54), DG, RW - 2 * M - 190, 1.2)
        y += hh + 50
    if s.get("footer"):
        y = para(d, (M, y + 40), s["footer"], F("Regular", 48), LM, RW - 2 * M)
    guard("reel checklist", y, RH - 300)
    r_foot(d, True, h)
    return [(im, s.get("seconds", 7))]


def r_cta(s, h):
    im, d = r_new(DG)
    y = 500
    if s.get("note"):
        y = para(d, (M, 500), s["note"], F("Medium", 50), LM, RW - 2 * M) + 110
    lines = len(wrap(d, s["text"], F("Bold", 62), RW - 2 * M - 96))
    d.rounded_rectangle((M, y, RW - M, y + lines * 75 + 110), radius=48, fill=AG)
    para(d, (M + 48, y + 55), s["text"], F("Bold", 62), DG, RW - 2 * M - 96, 1.2)
    guard("reel cta", y + lines * 75 + 110, RH - 300)
    r_foot(d, True, h)
    return [(im, s.get("seconds", 5))]


SCENE = {"hook": r_hook, "mistake": r_mistake, "prompt": r_prompt, "checklist": r_checklist, "cta": r_cta}


def render_reel(spec, out):
    os.makedirs(out, exist_ok=True)
    h = spec.get("handle", HANDLE_DEFAULT)
    frames = []
    for s in spec["scenes"]:
        frames += SCENE[s["type"]](s, h)
    total = sum(sec for _, sec in frames)
    if total < 15 or total > 45:
        WARN.append(f"Reel is {total:.0f}s; target is 15-45s.")
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "list.txt"), "w") as lst:
        for i, (im, sec) in enumerate(frames):
            im.save(os.path.join(tmp, f"f{i:03d}.png"))
            lst.write(f"file 'f{i:03d}.png'\nduration {sec}\n")
        lst.write(f"file 'f{len(frames) - 1:03d}.png'\n")
    frames[0][0].save(os.path.join(out, "cover.jpg"), quality=95)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", os.path.join(tmp, "list.txt"), "-vf", "fps=30,format=yuv420p",
                    "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart",
                    os.path.join(out, "reel.mp4")], check=True)
    shutil.rmtree(tmp)
    print(f"reel: {total:.0f}s -> {out}")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
        a = [x for x in a if x != only]
    if not a:
        raise SystemExit("Usage: python3 render.py SPEC.json [OUT_DIR] [--only carousel|reel]")
    spec = json.load(open(a[0]))
    repo = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    stem = os.path.splitext(os.path.basename(a[0]))[0]
    dirs = spec.get("output", {})

    def resolve(p):
        return os.path.expanduser(p) if os.path.isabs(os.path.expanduser(p)) else os.path.join(repo, p)

    if len(a) > 1:
        out = os.path.expanduser(a[1])
        cdir, rdir = os.path.join(out, "posts"), os.path.join(out, "reels")
    else:
        cdir = resolve(dirs.get("carousel_dir", f"aiflowed/posts/{stem}"))
        rdir = resolve(dirs.get("reel_dir", f"aiflowed/reels/{stem}"))
    print(f"carousel folder: {cdir}\nreel folder: {rdir}")
    if "carousel" in spec and only in (None, "carousel"):
        render_carousel(spec["carousel"], cdir)
    if "reel" in spec and only in (None, "reel"):
        render_reel(spec["reel"], rdir)
    for w in WARN:
        print("WARNING:", w)
