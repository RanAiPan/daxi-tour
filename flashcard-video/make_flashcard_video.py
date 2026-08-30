#!/usr/bin/env python3
"""Render a silent macaron-green flashcard-style quote video (MP4, no audio)."""

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent

CONFIG = dict(
    width=1080,
    height=1920,
    fps=30,
    duration=9.0,
    photo_path=ROOT / "assets" / "photo.jpg",
    output_path=ROOT / "output" / "quote_flashcard.mp4",
    bg_top=(235, 246, 231),
    bg_bottom=(198, 231, 204),
    glow_color=(255, 253, 246),
    card_border=(255, 253, 248),
    shadow_color=(96, 122, 98),
    leaf_color=(120, 151, 112),
    text_main=(74, 92, 75),
    text_accent=(178, 118, 96),
    card_width=820,
    card_border_px=22,
    card_radius=30,
    font_regular=("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc", 3),
    font_bold=("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", 3),
    lines=[
        dict(text="做和身份相符的事", accent=False),
        dict(text="說與年紀相稱的話", accent=False),
        dict(text="不掂起腳高攀", accent=False),
        dict(text="也不屈著膝低就", accent=False),
        dict(text="自己過的舒服", accent=True),
        dict(text="就是最好的活法", accent=True),
    ],
    line_size_regular=58,
    line_size_accent=66,
    line_gap=30,
    group_gap=42,
    text_top=990,
    intro_start=0.2,
    intro_dur=1.0,
    text_start=1.0,
    text_stagger=0.22,
    text_fade_dur=0.5,
    text_slide_px=22,
    fade_out_dur=1.0,
)


def make_background(cfg):
    h, w = cfg["height"], cfg["width"]
    top = np.array(cfg["bg_top"], dtype=np.float32)
    bottom = np.array(cfg["bg_bottom"], dtype=np.float32)
    t = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1, 1)
    grad = top.reshape(1, 1, 3) * (1 - t) + bottom.reshape(1, 1, 3) * t
    grad = np.repeat(grad, w, axis=1).astype(np.uint8)
    bg = Image.fromarray(grad, mode="RGB").convert("RGBA")

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gw, gh = int(w * 0.95), int(w * 0.95)
    gx, gy = (w - gw) // 2, int(h * 0.06)
    gd.ellipse([gx, gy, gx + gw, gy + gh], fill=(*cfg["glow_color"], 130))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    bg = Image.alpha_composite(bg, glow)
    return bg


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return mask


def make_card_sprite(cfg):
    photo = Image.open(cfg["photo_path"]).convert("RGB")
    border = cfg["card_border_px"]
    inner_w = cfg["card_width"] - 2 * border
    inner_h = int(inner_w * photo.height / photo.width)
    photo = photo.resize((inner_w, inner_h), Image.LANCZOS)

    card_w = inner_w + 2 * border
    card_h = inner_h + 2 * border
    pad = 60
    sprite = Image.new("RGBA", (card_w + pad * 2, card_h + pad * 2), (0, 0, 0, 0))

    shadow = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [pad, pad + 16, pad + card_w, pad + card_h + 16],
        radius=cfg["card_radius"],
        fill=(*cfg["shadow_color"], 90),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    sprite = Image.alpha_composite(sprite, shadow)

    frame = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    fd.rounded_rectangle(
        [pad, pad, pad + card_w, pad + card_h],
        radius=cfg["card_radius"],
        fill=(*cfg["card_border"], 255),
    )
    sprite = Image.alpha_composite(sprite, frame)

    photo_rgba = photo.convert("RGBA")
    photo_mask = rounded_mask(photo.size, max(cfg["card_radius"] - border, 6))
    sprite.paste(photo_rgba, (pad + border, pad + border), photo_mask)

    return sprite, (card_w + pad * 2, card_h + pad * 2), pad


def make_leaf_sprite(cfg):
    size = 90
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    d.line([(cx, cy - 20), (cx, cy + 20)], fill=(*cfg["leaf_color"], 220), width=3)
    for dx, dy, ang in [(-16, -8, -35), (16, -8, 35), (-14, 8, -35), (14, 8, 35)]:
        leaf = Image.new("RGBA", (34, 20), (0, 0, 0, 0))
        ld = ImageDraw.Draw(leaf)
        ld.ellipse([0, 0, 34, 20], fill=(*cfg["leaf_color"], 200))
        leaf = leaf.rotate(ang, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(leaf, (cx + dx - leaf.width // 2, cy + dy - leaf.height // 2))
    return img


def build_font(spec, size):
    path, index = spec
    return ImageFont.truetype(path, size, index=index)


def make_text_layers(cfg):
    w, h = cfg["width"], cfg["height"]
    font_reg = None
    font_accent = None
    layers = []
    y = cfg["text_top"]
    prev_group_accent = None
    for i, line in enumerate(cfg["lines"]):
        accent = line["accent"]
        size = cfg["line_size_accent"] if accent else cfg["line_size_regular"]
        font = build_font(cfg["font_bold"] if accent else cfg["font_regular"], size)
        color = cfg["text_accent"] if accent else cfg["text_main"]

        if prev_group_accent is not None and prev_group_accent != accent:
            y += cfg["group_gap"]
        prev_group_accent = accent

        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        bbox = d.textbbox((0, 0), line["text"], font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2 - bbox[0]
        d.text((x, y), line["text"], font=font, fill=(*color, 255))
        layers.append(layer)

        y += size + cfg["line_gap"]

    return layers


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def render(cfg):
    w, h, fps, dur = cfg["width"], cfg["height"], cfg["fps"], cfg["duration"]
    n_frames = int(round(dur * fps))

    bg = make_background(cfg)
    card_sprite, card_size, card_pad = make_card_sprite(cfg)
    leaf = make_leaf_sprite(cfg)
    text_layers = make_text_layers(cfg)

    card_x = (w - card_size[0]) // 2
    card_y = 190 - card_pad
    leaf_x = (w - leaf.width) // 2
    leaf_y = 190 + (card_size[1] - 2 * card_pad) + 40

    intro_start, intro_end = cfg["intro_start"], cfg["intro_start"] + cfg["intro_dur"]
    text_fade_end = cfg["text_start"] + (len(text_layers) - 1) * cfg["text_stagger"] + cfg["text_fade_dur"]
    hold_start = text_fade_end
    fade_out_start = dur - cfg["fade_out_dur"]

    cached_hold_frame = None

    cfg["output_path"].parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{w}x{h}", "-framerate", str(fps),
        "-i", "-",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
        str(cfg["output_path"]),
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    for i in range(n_frames):
        t = i / fps
        in_hold = hold_start <= t < fade_out_start

        if in_hold and cached_hold_frame is not None:
            proc.stdin.write(cached_hold_frame)
            continue

        frame = bg.copy()

        card_p = ease_out((t - intro_start) / cfg["intro_dur"])
        if card_p > 0:
            scale = 0.94 + 0.06 * card_p
            alpha = card_p
            cw = max(1, int(card_size[0] * scale))
            ch = max(1, int(card_size[1] * scale))
            scaled = card_sprite.resize((cw, ch), Image.LANCZOS)
            if alpha < 1.0:
                a = scaled.split()[3].point(lambda v: int(v * alpha))
                scaled.putalpha(a)
            cx = card_x + (card_size[0] - cw) // 2
            cy = card_y + (card_size[1] - ch) // 2
            frame.alpha_composite(scaled, (cx, cy))
            frame.alpha_composite(leaf, (leaf_x, leaf_y))

        for idx, layer in enumerate(text_layers):
            start = cfg["text_start"] + idx * cfg["text_stagger"]
            p = ease_out((t - start) / cfg["text_fade_dur"])
            if p <= 0:
                continue
            offset = int(cfg["text_slide_px"] * (1 - p))
            shifted = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            shifted.paste(layer, (0, offset))
            if p < 1.0:
                a = shifted.split()[3].point(lambda v, p=p: int(v * p))
                shifted.putalpha(a)
            frame.alpha_composite(shifted)

        if t >= fade_out_start:
            fp = ease_out((t - fade_out_start) / cfg["fade_out_dur"])
            fg_alpha = 1.0 - fp
            faded = Image.blend(bg, frame, fg_alpha)
            frame = faded

        rgb = np.array(frame.convert("RGB"), dtype=np.uint8)
        data = rgb.tobytes()
        proc.stdin.write(data)

        if in_hold and cached_hold_frame is None:
            cached_hold_frame = data

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        sys.exit(f"ffmpeg exited with code {proc.returncode}")
    print(f"Wrote {cfg['output_path']} ({n_frames} frames, {dur}s @ {fps}fps)")


if __name__ == "__main__":
    render(CONFIG)
