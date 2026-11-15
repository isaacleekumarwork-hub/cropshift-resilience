"""Paint the Starry Night theme's artwork as SVG (patch A9.UI.1).

Run from the repository root:

    .venv/bin/python scripts/make_theme_artwork.py

It writes deterministic SVG files to ``static/theme/`` (same seed, same
output). Nothing here is imported by the app.

The artwork is original. It borrows the *language* of Post-Impressionist oil
painting (short directional brushstrokes, swirling wind, haloed stars, a
crescent moon, rolling fields and golden wheat) from Vincent van Gogh's
public-domain painting The Starry Night (1889) and his wheat-field paintings,
but copies no painting. The landscape is imaginary: it is not a picture of
the provisional Katumani pilot area.

Each stroke is a short quadratic curve laid along a flow field (a gentle wave
of wind plus a few vortices). A thin, lighter copy of every stroke, offset up
and to the left, suggests raised paint catching light (impasto).

AI assistance: this script and the artwork it produces were made with Claude
Code (Anthropic) under the participant's direction during the 2026 NASA Space
Apps Challenge. The artwork is watermarked as AI-generated (SI). See
docs/provenance.md.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "theme"
WATERMARK = "Original AI-generated artwork (SI) · after Vincent van Gogh, The Starry Night (1889) · imaginary landscape"

# Night sky ramp, dark to light, from the theme palette (#101B38 ... #F4E8C8).
SKY = ["#0D1631", "#101B38", "#16295A", "#1C3567", "#24477A", "#2E5A8F", "#3E6E9E", "#527DA6", "#7E9FC2", "#A9C1DA", "#C8D6E9"]
STAR = ["#F3C94E", "#F6D777", "#F4E8C8", "#E2B13C", "#FFF1B8"]
# Fields at night under moonlight: blue-green, olive, ochre and golden wheat.
FIELDS = [
    ("#183056", ["#1F3D6B", "#2A4F80", "#13264A"]),
    ("#2C4A44", ["#3B5E55", "#22403A", "#4E7268"]),
    ("#7A5A1E", ["#9C7428", "#5E4416", "#B88A33"]),
    ("#3A4628", ["#4E5C33", "#2C3820", "#66733F"]),
]
WHEAT = ["#E2B13C", "#F3C94E", "#C99A2E", "#F4E8C8", "#A97E26"]


def _flow(x: float, y: float, vortices: list[tuple[float, float, float, float]]) -> tuple[float, float]:
    """Direction of the wind at (x, y), and how strongly a vortex bends it."""
    tilt = 0.32 * math.sin(x / 170 + y / 95) + 0.12 * math.sin(x / 61)
    vx, vy, bend = math.cos(tilt), math.sin(tilt), 0.0
    for cx, cy, radius, spin in vortices:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1.0
        w = math.exp(-((d / radius) ** 2))
        vx += spin * w * 2.4 * (-dy / d)
        vy += spin * w * 2.4 * (dx / d)
        bend += spin * w
    return math.atan2(vy, vx), bend


def _stroke(x: float, y: float, angle: float, length: float, curve: float) -> str:
    """A short quadratic brushstroke centred on (x, y), in relative path syntax."""
    ux, uy = math.cos(angle), math.sin(angle)
    x0, y0 = x - ux * length / 2, y - uy * length / 2
    ex, ey = ux * length, uy * length
    qx, qy = ex / 2 - uy * curve, ey / 2 + ux * curve
    return f"M{x0:.0f} {y0:.0f}q{qx:.0f} {qy:.0f} {ex:.0f} {ey:.0f}"


class Canvas:
    """Strokes grouped by colour, width and opacity, so attributes are written once per group."""

    def __init__(self) -> None:
        self.groups: dict[tuple[str, int, float], list[str]] = defaultdict(list)
        self.impasto: list[str] = []

    def add(self, d: str, colour: str, width: int, opacity: float, raised: bool = True) -> None:
        self.groups[(colour, width, opacity)].append(d)
        if raised:
            self.impasto.append(d)

    def svg(self, order: list[str]) -> list[str]:
        rank = {colour: i for i, colour in enumerate(order)}
        out = []
        for (colour, width, opacity), paths in sorted(self.groups.items(), key=lambda item: (rank.get(item[0][0], 99), -item[0][1])):
            out.append(f'<path fill="none" stroke="{colour}" stroke-width="{width}" stroke-opacity="{opacity}" stroke-linecap="round" d="{"".join(paths)}"/>')
        if self.impasto:
            out.append(
                '<path fill="none" stroke="#F4E8C8" stroke-width="1.3" stroke-opacity="0.2" stroke-linecap="round" '
                f'transform="translate(-1.6 -1.6)" d="{"".join(self.impasto)}"/>'
            )
        return out


def _paint_sky(canvas: Canvas, rng: random.Random, width: int, top: int, bottom: int, spacing: int,
               vortices: list[tuple[float, float, float, float]], glow: list[tuple[float, float, float]]) -> None:
    for gy in range(top, bottom, spacing):
        for gx in range(-spacing, width + spacing, spacing):
            x = gx + rng.uniform(-spacing * 0.45, spacing * 0.45)
            y = gy + rng.uniform(-spacing * 0.45, spacing * 0.45)
            angle, bend = _flow(x, y, vortices)
            light = 1.2 + 4.6 * (y - top) / max(bottom - top, 1) + rng.uniform(-1.3, 1.3)
            for cx, cy, r in glow:
                light += 4.2 * math.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / (r * r)))
            light += 2.5 * min(abs(bend), 1.0)
            colour = SKY[max(0, min(len(SKY) - 1, int(round(light))))]
            length = rng.uniform(16, 32)
            canvas.add(
                _stroke(x, y, angle, length, rng.uniform(-3.5, 3.5) + 7 * bend),
                colour, rng.choice((5, 7, 7, 9)), rng.choice((0.75, 0.9, 1.0)),
            )


def _paint_star(canvas: Canvas, rng: random.Random, cx: float, cy: float, r: float, core: bool = True) -> None:
    """Concentric halos of loose dabs, pale blue outside and gold within, around a bright core."""
    rings = (
        (1.5, ["#7E9FC2", "#A9C1DA", "#C8D6E9"], 15, 5),
        (1.18, ["#C8D6E9", "#F4E8C8", "#E2B13C"], 13, 5),
        (0.88, STAR[:3], 11, 4),
        (0.6, STAR[1:4], 9, 4),
    )
    for ring, colours, dab, width in rings:
        radius = r * ring
        count = max(8, int(2 * math.pi * radius / (dab * 0.95)))
        for i in range(count):
            a = 2 * math.pi * i / count + rng.uniform(-0.12, 0.12)
            rr = radius * rng.uniform(0.9, 1.1)
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            canvas.add(
                _stroke(x, y, a + math.pi / 2 + rng.uniform(-0.25, 0.25), dab * rng.uniform(0.7, 1.25), rng.uniform(-2.5, 2.5)),
                rng.choice(colours), width, rng.choice((0.75, 0.9, 1.0)),
            )
    if not core:
        return
    for i in range(12):
        a = 2 * math.pi * i / 12 + rng.uniform(-0.25, 0.25)
        x, y = cx + r * 0.16 * math.cos(a), cy + r * 0.16 * math.sin(a)
        canvas.add(_stroke(x, y, a + rng.uniform(-0.3, 0.3), r * rng.uniform(0.22, 0.36), rng.uniform(-2, 2)), rng.choice(STAR), 5, 1.0)


def _ridge(x: float, base: float, amp: float, period: float, phase: float) -> float:
    return base + amp * math.sin(x / period + phase) + amp * 0.35 * math.sin(x / (period * 0.37) + phase * 2)


def _paint_fields(canvas: Canvas, rng: random.Random, width: int, height: int, horizon: int, bands: int) -> list[str]:
    """Rolling fields under the horizon; returns the filled field shapes (drawn under the strokes)."""
    shapes = []
    ridges = []
    span = height - horizon
    for i in range(bands):
        base = horizon + span * (i / bands) * 0.92
        ridges.append((base, 10 + 6 * i, 140 + 60 * i, rng.uniform(0, 6)))
    # Far to near: blue hills, green pasture, ochre stubble, golden wheat, dark olive foreground.
    sequence = [0, 1, 2, 3][: bands - 2] + [None, 3]
    for i, (base, amp, period, phase) in enumerate(ridges):
        kind = sequence[i] if i < len(sequence) else 3
        fill, stroke_colours = (WHEAT[2], WHEAT) if kind is None else FIELDS[kind]
        top = " ".join(f"{x} {_ridge(x, base, amp, period, phase):.0f}" for x in range(0, width + 41, 40))
        shapes.append(f'<path fill="{fill}" d="M0 {height}L{top}L{width} {height}Z"/>')
        nxt = ridges[i + 1][0] if i + 1 < bands else height + 20
        wheat = kind is None
        step = 9 if wheat else 15
        for gy in range(int(base) + 6, int(nxt) + 12, step):
            for gx in range(-10, width + 10, step + 4):
                x = gx + rng.uniform(-5, 5)
                y = gy + rng.uniform(-4, 4)
                if y < _ridge(x, base, amp, period, phase) + 3:
                    continue
                if wheat:
                    angle = -math.pi / 2 + rng.uniform(-0.35, 0.35) + 0.25 * math.sin(x / 90)
                    canvas.add(_stroke(x, y, angle, rng.uniform(12, 20), rng.uniform(-2, 2)), rng.choice(WHEAT), rng.choice((3, 4)), rng.choice((0.8, 1.0)))
                else:
                    slope = math.atan(amp / period * math.cos(x / period + phase))
                    canvas.add(_stroke(x, y, slope + rng.uniform(-0.12, 0.12), rng.uniform(18, 30), rng.uniform(-2, 2)),
                               rng.choice(stroke_colours), rng.choice((4, 5)), rng.choice((0.7, 0.85)))
    return shapes


def background() -> str:
    rng = random.Random(1889)
    width, height, horizon = 1600, 1000, 690
    vortices = [(820, 360, 170, 1.0), (460, 300, 90, -0.8), (1180, 420, 110, 0.7)]
    glow = [(820, 360, 120), (1420, 120, 120)]
    canvas = Canvas()
    _paint_sky(canvas, rng, width, 0, horizon + 20, 24, vortices, glow)
    for cx, cy, r in [(170, 135, 48), (345, 245, 36), (560, 115, 52), (705, 250, 30), (1010, 130, 44),
                      (1160, 285, 34), (1275, 160, 30), (70, 330, 30), (1530, 330, 36), (250, 520, 24), (1345, 525, 26)]:
        _paint_star(canvas, rng, cx, cy, r)
    moon_ring = Canvas()
    _paint_star(moon_ring, rng, 1425, 120, 88, core=False)
    fields = Canvas()
    shapes = _paint_fields(fields, rng, width, height, horizon, 5)
    order = SKY + STAR
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid slice">',
        "<title>Swirling night sky with stars and a crescent moon over rolling fields and golden wheat</title>",
        "<desc>Original artwork generated with AI assistance (SI) for CropShift RESILIENCE, in the manner of "
        "Post-Impressionist oil painting and inspired by Vincent van Gogh's The Starry Night (1889, public domain). "
        "Not a reproduction of any painting. The landscape is imaginary and is not the project's pilot site.</desc>",
        f'<rect width="{width}" height="{height}" fill="#16295A"/>',
        *canvas.svg(order),
        *moon_ring.svg(order),
        '<path d="M1400 62A62 62 0 1 0 1474 160A50 50 0 1 1 1400 62Z" fill="#F3C94E"/>',
        '<path d="M1408 80A44 44 0 0 0 1452 152" fill="none" stroke="#FFF1B8" stroke-width="5" stroke-linecap="round" stroke-opacity="0.8"/>',
        *shapes,
        *fields.svg([f for f, _ in FIELDS] + [c for _, cs in FIELDS for c in cs] + WHEAT),
        '<g fill="#0D1631"><path d="M1186 742h46v-26l-23-18-23 18z"/><path d="M1240 742h30v-18h-30z"/></g>',
        '<g fill="#F3C94E"><rect x="1196" y="724" width="7" height="8"/><rect x="1216" y="724" width="7" height="8"/><rect x="1250" y="730" width="6" height="6"/></g>',
        f'<text x="{width / 2:.0f}" y="{height - 14}" text-anchor="middle" font-family="Georgia, serif" font-size="13" '
        f'fill="#F4E8C8" fill-opacity="0.85">{WATERMARK}</text>',
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def banner() -> str:
    """A wide painted strip for the top of the page: wind, two stars, wheat."""
    rng = random.Random(1890)
    width, height, horizon = 1600, 200, 132
    canvas = Canvas()
    _paint_sky(canvas, rng, width, 0, horizon + 10, 16, [(560, 70, 70, 1.0), (1180, 80, 60, -0.8)], [(560, 70, 60)])
    _paint_star(canvas, rng, 300, 52, 26)
    _paint_star(canvas, rng, 1420, 60, 30)
    fields = Canvas()
    shapes = _paint_fields(fields, rng, width, height, horizon, 3)
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid slice">',
        "<title>Painted strip of swirling wind, stars and a wheat field</title>",
        "<desc>Original AI-generated (SI) artwork for CropShift RESILIENCE, after Vincent van Gogh. Imaginary landscape.</desc>",
        f'<rect width="{width}" height="{height}" fill="#16295A"/>',
        *canvas.svg(SKY + STAR),
        *shapes,
        *fields.svg([f for f, _ in FIELDS] + [c for _, cs in FIELDS for c in cs] + WHEAT),
        "</svg>",
    ]) + "\n"


def frame() -> str:
    """A 120 x 120 brushed border for CSS border-image (slice 30): rough strokes, transparent middle."""
    rng = random.Random(1891)
    canvas = Canvas()
    colours = ["#24477A", "#527DA6", "#2E5A8F", "#C8D6E9", "#F3C94E"]
    weights = [5, 4, 3, 1, 1]
    for _ in range(3):
        for edge in range(4):
            for t in range(6, 120, 9):
                inset = rng.uniform(7, 17)
                x, y, angle = {
                    0: (t, inset, 0.0), 1: (120 - inset, t, math.pi / 2),
                    2: (t, 120 - inset, 0.0), 3: (inset, t, math.pi / 2),
                }[edge]
                colour = rng.choices(colours, weights)[0]
                canvas.add(_stroke(x, y, angle + rng.uniform(-0.15, 0.15), rng.uniform(14, 22), rng.uniform(-2, 2)),
                           colour, rng.choice((4, 5, 6)), rng.choice((0.85, 1.0)))
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">',
        *canvas.svg(colours),
        "</svg>",
    ]) + "\n"


def underline() -> str:
    """A gold brushstroke for headings and the selected tab."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 16" preserveAspectRatio="none">'
        '<path d="M4 10C70 5 150 12 296 6" fill="none" stroke="#E2B13C" stroke-width="7" stroke-linecap="round" stroke-opacity="0.9"/>'
        '<path d="M10 9C90 6 170 11 288 7" fill="none" stroke="#F3C94E" stroke-width="4" stroke-linecap="round"/>'
        '<path d="M30 7C110 5 190 9 270 6" fill="none" stroke="#FFF1B8" stroke-width="1.5" stroke-linecap="round" stroke-opacity="0.7"/>'
        "</svg>\n"
    )


def divider() -> str:
    """A long horizontal stroke of blues with a thread of gold."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 14" preserveAspectRatio="none">'
        '<path d="M6 8C300 3 600 12 900 6S1150 9 1194 7" fill="none" stroke="#24477A" stroke-width="8" stroke-linecap="round"/>'
        '<path d="M20 7C320 4 610 10 910 7S1140 8 1180 6" fill="none" stroke="#527DA6" stroke-width="4" stroke-linecap="round"/>'
        '<path d="M120 6C400 5 700 9 1000 6" fill="none" stroke="#F3C94E" stroke-width="1.6" stroke-linecap="round" stroke-opacity="0.8"/>'
        "</svg>\n"
    )


def edge() -> str:
    """A vertical stroke for the sidebar's edge."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 800" preserveAspectRatio="none">'
        '<path d="M8 4C4 200 11 400 6 600S9 760 7 796" fill="none" stroke="#24477A" stroke-width="8" stroke-linecap="round"/>'
        '<path d="M7 10C5 210 10 410 6 610S8 770 7 790" fill="none" stroke="#F3C94E" stroke-width="2" stroke-linecap="round" stroke-opacity="0.75"/>'
        "</svg>\n"
    )


def grain() -> str:
    """A small tile of canvas grain (fractal noise), laid over the outer background only."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180" viewBox="0 0 180 180">'
        '<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch"/>'
        '<feColorMatrix values="0 0 0 0 0.96  0 0 0 0 0.91  0 0 0 0 0.78  0 0 0 0.55 -0.12"/></filter>'
        '<rect width="180" height="180" filter="url(#g)"/>'
        "</svg>\n"
    )


ARTWORK = {
    "starry_night_background.svg": background,
    "starry_night_banner.svg": banner,
    "brush_frame.svg": frame,
    "brush_underline.svg": underline,
    "brush_divider.svg": divider,
    "brush_edge.svg": edge,
    "canvas_grain.svg": grain,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, painter in ARTWORK.items():
        text = painter()
        (OUT / name).write_text(text, encoding="utf-8")
        print(f"{name}: {len(text.encode()) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
