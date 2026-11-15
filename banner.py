#!/usr/bin/env python3
"""Draws banner_light.svg / banner_dark.svg: a whoami prompt over pixel hills."""

import base64
import math
from pathlib import Path

ROOT = Path(__file__).parent
W, H, PX = 880, 300, 8
MONO = "Iosevka,ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
PIXEL = "'Geist Pixel Square'," + MONO
# Same faces as trine.dev, embedded so the banner never falls back to the viewer's fonts.
FONTS = [
    ("Iosevka", 400, "Iosevka-400-subset.woff2"),
    ("Iosevka", 500, "Iosevka-500-subset.woff2"),
    ("Geist Pixel Square", 500, "GeistPixel-Square.woff2"),
]


def font_faces():
    faces = []
    for family, weight, name in FONTS:
        data = base64.b64encode((ROOT / "fonts" / name).read_bytes()).decode()
        faces.append(f"@font-face{{font-family:'{family}';font-weight:{weight};src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return "".join(faces)

THEMES = {
    "light": {
        "sky": "#e6e9e3", "fg": "#26302b", "dim": "#6b766f", "accent": "#b5652e",
        "hills": ["#cdd3cb", "#a9b4aa", "#7f8f83", "#56685c", "#3a4a40"],
    },
    "dark": {
        "sky": "#151a17", "fg": "#e3e8e2", "dim": "#8a968d", "accent": "#e08a4f",
        "hills": ["#1d2420", "#26302a", "#313d35", "#3d4b41", "#4a5a4f"],
    },
}

# Each ridge: base height (fraction of H), then (amplitude, wavelength, phase) terms.
RIDGES = [
    (0.42, [(34, 520, 0.4), (14, 170, 1.9)]),
    (0.34, [(26, 380, 2.2), (10, 120, 0.7)]),
    (0.26, [(20, 300, 4.1), (8, 90, 2.6)]),
    (0.17, [(14, 240, 1.3), (6, 70, 5.0)]),
    (0.09, [(6, 200, 3.3), (4, 60, 0.2)]),
]


def ridge_top(x, base, terms):
    y = H * (1 - base)
    for amp, wave, phase in terms:
        y -= amp * math.sin(2 * math.pi * x / wave + phase)
    # Keep the text corner clear: the hills fall away toward the left.
    y += max(0, 520 - x) * 0.12
    return round(y / PX) * PX


def pine(x, ground, height, color):
    rects = []
    for row in range(height):
        # Canopy widens every other row; the last row is the trunk.
        width = PX * (1 + 2 * (row // 2)) if row < height - 1 else PX
        rects.append(f'<rect x="{x - width // 2}" y="{ground - (height - row) * PX}" width="{width}" height="{PX}" fill="{color}"/>')
    return rects


def render(theme):
    c = THEMES[theme]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{MONO}" shape-rendering="crispEdges">',
        "<style>" + font_faces() + "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        ".cursor{animation:blink 1.1s steps(1) infinite}"
        "@media (prefers-reduced-motion:reduce){.cursor{animation:none}}</style>",
        f'<rect width="{W}" height="{H}" rx="10" fill="{c["sky"]}"/>',
        '<clipPath id="card"><rect width="{0}" height="{1}" rx="10"/></clipPath><g clip-path="url(#card)">'.format(W, H),
    ]
    for i, (base, terms) in enumerate(RIDGES):
        color = c["hills"][i]
        for x in range(0, W, PX):
            top = ridge_top(x + PX / 2, base, terms)
            out.append(f'<rect x="{x}" y="{top}" width="{PX}" height="{H - top}" fill="{color}"/>')
        if i in (2, 3):
            for tx in range(560 + i * 37, W, 61 + i * 23):
                ground = ridge_top(tx, base, terms)
                out += pine(tx, ground + PX, 6 + (tx // 7) % 3, c["hills"][min(i + 1, 4)])
    out.append("</g>")

    out += [
        f'<text x="40" y="58" font-size="16" fill="{c["accent"]}">$ <tspan fill="{c["dim"]}">whoami</tspan></text>',
        f'<text x="40" y="108" font-size="46" font-weight="500" font-family="{PIXEL}" fill="{c["fg"]}">zerone0x</text>',
        f'<text x="40" y="150" font-size="19" fill="{c["fg"]}">Build tools. Break systems.</text>',
        # The cursor rides in the same text run, so it sits right whatever mono font the viewer has.
        f'<text x="40" y="178" font-size="19" fill="{c["fg"]}">Live in the terminal.<tspan class="cursor" fill="{c["accent"]}">█</tspan></text>',
        "</svg>",
    ]
    return "\n".join(out)


def main():
    for theme in THEMES:
        (ROOT / f"banner_{theme}.svg").write_text(render(theme))


if __name__ == "__main__":
    main()
