"""Draw the Starry Night theme's brushstroke ornaments as SVG (patch A9.UI.1).

Run from the repository root:

    .venv/bin/python scripts/make_theme_artwork.py

It writes deterministic SVG files to ``static/theme/`` (same seed, same
output): a brushed frame for the main canvas, a gold underline for headings
and the selected tab, a painted divider, a brushed sidebar edge and a small
canvas-grain tile. Nothing here is imported by the app.

The theme's painting itself (``wheatfield_night_*.jpg``) is not drawn here: it
is an AI-generated image the participant created and supplied, a wheat field
under a swirling night sky in the style of Vincent van Gogh.

AI assistance: this script was written with Claude Code (Anthropic) under the
participant's direction during the 2026 NASA Space Apps Challenge. See
docs/provenance.md.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "theme"


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

    def add(self, d: str, colour: str, width: int, opacity: float) -> None:
        self.groups[(colour, width, opacity)].append(d)
        self.impasto.append(d)

    def svg(self, order: list[str]) -> list[str]:
        rank = {colour: i for i, colour in enumerate(order)}
        out = []
        for (colour, width, opacity), paths in sorted(self.groups.items(), key=lambda item: (rank.get(item[0][0], 99), -item[0][1])):
            out.append(f'<path fill="none" stroke="{colour}" stroke-width="{width}" stroke-opacity="{opacity}" stroke-linecap="round" d="{"".join(paths)}"/>')
        out.append(
            '<path fill="none" stroke="#F4E8C8" stroke-width="1.3" stroke-opacity="0.2" stroke-linecap="round" '
            f'transform="translate(-1.6 -1.6)" d="{"".join(self.impasto)}"/>'
        )
        return out


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
