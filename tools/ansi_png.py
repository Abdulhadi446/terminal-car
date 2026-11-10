#!/usr/bin/env python3
"""Render `tmux capture-pane -e` output to a PNG for visual testing.

Usage:
    python tools/ansi_png.py capture.txt out.png [--cols 206]

The input should be the ANSI-coloured text from:
    tmux capture-pane -e -p -t rush > /tmp/rush.ansi
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
from pathlib import Path

SGR = re.compile(r"\x1b\[([0-9;]*)m")
CSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def xterm_rgb(index: int) -> tuple[int, int, int]:
    base = [
        (0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
        (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
        (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
        (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
    ]
    if index < 16:
        return base[index]
    if index < 232:
        n = index - 16
        levels = (0, 95, 135, 175, 215, 255)
        return levels[n // 36], levels[(n // 6) % 6], levels[n % 6]
    level = 8 + (index - 232) * 10
    return level, level, level


def parse_ansi(data: str, cols: int) -> list[list[tuple[str, int, int, int]]]:
    rows: list[list[tuple[str, int, int, int]]] = []
    row: list[tuple[str, int, int, int]] = []
    fg, bg, attr = 252, 233, 0
    pos = 0
    while pos < len(data):
        match = SGR.match(data, pos)
        if match:
            codes = [int(part) if part else 0 for part in match.group(1).split(";")]
            i = 0
            while i < len(codes):
                code = codes[i]
                if code == 0:
                    fg, bg, attr = 252, 233, 0
                elif code == 1:
                    attr |= 1
                elif code == 7:
                    attr |= 2
                elif code == 22:
                    attr &= ~1
                elif code == 27:
                    attr &= ~2
                elif code == 39:
                    fg = 252
                elif code == 49:
                    bg = 233
                elif code == 38 and i + 2 < len(codes) and codes[i + 1] == 5:
                    fg = codes[i + 2]
                    i += 2
                elif code == 48 and i + 2 < len(codes) and codes[i + 1] == 5:
                    bg = codes[i + 2]
                    i += 2
                elif 30 <= code <= 37:
                    fg = code - 30
                elif 40 <= code <= 47:
                    bg = code - 40
                elif 90 <= code <= 97:
                    fg = code - 90 + 8
                elif 100 <= code <= 107:
                    bg = code - 100 + 8
                i += 1
            pos = match.end()
            continue
        match = CSI.match(data, pos)
        if match:
            pos = match.end()
            continue
        char = data[pos]
        pos += 1
        if char == "\x1b":
            continue
        if char == "\r":
            row = []
            continue
        if char == "\n":
            rows.append(row)
            row = []
            continue
        if char == "\t":
            while len(row) % 8:
                row.append((" ", fg, bg, attr))
            continue
        if attr & 2:
            row.append((char, bg, fg, attr & ~2))
        else:
            row.append((char, fg, bg, attr))
    if row:
        rows.append(row)
    for line in rows:
        line.extend([(" ", 252, 233, 0)] * (cols - len(line)))
    return rows


def make_svg(rows, cw=13, ch=24, font_size=20) -> str:
    height = len(rows) * ch
    width = max(len(line) for line in rows) * cw
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#1b1b1b"/>',
        f'<g font-family="JetBrainsMono Nerd Font, monospace" font-size="{font_size}" '
        'xml:space="preserve">',
    ]
    for y, line in enumerate(rows):
        # Background runs to keep the SVG compact.
        x = 0
        while x < len(line):
            bg = line[x][2]
            start = x
            while x < len(line) and line[x][2] == bg:
                x += 1
            r, g, b = xterm_rgb(bg)
            out.append(
                f'<rect x="{start * cw}" y="{y * ch}" width="{(x - start) * cw}" '
                f'height="{ch}" fill="#{r:02x}{g:02x}{b:02x}"/>'
            )
        for x, (char, fg, _bg, attr) in enumerate(line):
            if char == " ":
                continue
            r, g, b = xterm_rgb(fg)
            weight = ' font-weight="bold"' if attr & 1 else ""
            out.append(
                f'<text x="{x * cw}" y="{y * ch + ch * 0.78:.1f}" fill="#{r:02x}{g:02x}{b:02x}"'
                f'{weight}>{html.escape(char)}</text>'
            )
    out.append("</g></svg>")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cols", type=int, default=0, help="columns; detected from longest line by default")
    parser.add_argument("--cell-width", type=int, default=13)
    parser.add_argument("--cell-height", type=int, default=24)
    parser.add_argument("--font-size", type=int, default=20)
    args = parser.parse_args()
    data = args.input.read_text(encoding="utf-8", errors="replace")
    plain = SGR.sub("", CSI.sub("", data))
    cols = args.cols or max(len(line) for line in plain.splitlines())
    rows = parse_ansi(data, cols)
    svg = make_svg(rows, args.cell_width, args.cell_height, args.font_size)
    svg_path = args.output.with_suffix(".svg")
    svg_path.write_text(svg, encoding="utf-8")
    subprocess.run(["convert", "-background", "none", str(svg_path), str(args.output)], check=True)
    print(f"wrote {args.output} ({cols} columns, {len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
