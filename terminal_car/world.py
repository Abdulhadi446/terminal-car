"""World colour grid, road backdrop and scenery helpers."""

from __future__ import annotations

from .constants import C, LANES
from .layout import Layout
from .sprites import Sprite
from .terminal import GLYPHS
from .utils import hash2d

GRASS_FILL = C["grass0"]
ROAD_FILL = C["road1"]


class Backdrop:
    """Static grass/asphalt texture generated once per terminal size."""

    def __init__(self, layout: Layout):
        self.layout = layout
        self.w = layout.cols
        self.h = layout.world_half
        self.rows: list[list[int]] = []
        self._build()

    def _build(self) -> None:
        lay = self.layout
        road_l = lay.road_x
        road_r = lay.road_right
        line_w = max(1, lay.scale // 2)
        center = road_l + lay.road_w // 2
        half_gap = max(1, lay.scale // 2)

        for y in range(self.h):
            row: list[int] = []
            for x in range(self.w):
                if road_l <= x < road_r:
                    color = ROAD_FILL
                    n = hash2d(x, y, 31) % 100
                    if n < 5:
                        color = C["road0"]
                    elif n < 11:
                        color = C["road2"]
                    elif n < 14:
                        color = C["road3"]
                    elif n < 16:
                        color = C["road_dark"]
                    # faint tyre wear strips in every lane
                    lane = (x - road_l) // lay.lane_w
                    lane_off = (x - road_l) % lay.lane_w
                    for wheel in (lay.lane_w * 0.28, lay.lane_w * 0.72):
                        if abs(lane_off - wheel) <= (0.65 * lay.scale):
                            if n < 45:
                                color = C["road0"]
                    row.append(color)
                else:
                    n = hash2d(x, y, 11) % 1000
                    if n < 4:
                        color = C["flower"]
                    elif n < 10:
                        color = C["grass2"]
                    elif n < 32:
                        color = C["grass1"]
                    elif n < 40:
                        color = C["grass3"]
                    else:
                        color = C["grass0"]
                    row.append(color)
            self.rows.append(row)

        # shoulders / gutters just outside the painted edge line
        for y in range(self.h):
            for x in (road_l - 1, road_r):
                if 0 <= x < self.w:
                    self.rows[y][x] = C["shoulder"]

        # white edge lines
        for y in range(self.h):
            n = hash2d(y, 0, 91) % 100
            shade = C["line_dim"] if n < 8 else C["line_white"]
            for k in range(line_w):
                for x in (road_l + 1 + k, road_r - 1 - k):
                    if 0 <= x < self.w:
                        self.rows[y][x] = shade

        # double yellow centre divider
        for y in range(self.h):
            tone = C["line_yellow"] if (y // max(1, 2 * lay.scale)) % 2 == 0 else C["line_yellow2"]
            for k in range(line_w):
                xl = center - half_gap - 1 - k
                xr = center + half_gap + k
                if 0 <= xl < self.w:
                    self.rows[y][xl] = tone
                if 0 <= xr < self.w:
                    self.rows[y][xr] = tone


class World:
    def __init__(self, layout: Layout, backdrop: Backdrop):
        self.layout = layout
        self.backdrop = backdrop
        self.w = layout.cols
        self.h = layout.world_half
        self.rows = [row[:] for row in backdrop.rows]

    def reset(self, dx: int = 0, dy: int = 0) -> None:
        if dx == 0 and dy == 0:
            self.rows = [row[:] for row in self.backdrop.rows]
            return
        grass = C["grass0"]
        bh = self.h
        bw = self.w
        src = self.backdrop.rows
        out: list[list[int]] = []
        for y in range(bh):
            sy = y - dy
            if sy < 0 or sy >= bh:
                out.append([grass] * bw)
                continue
            srow = src[sy]
            row: list[int] = []
            for x in range(bw):
                sx = x - dx
                row.append(srow[sx] if 0 <= sx < bw else grass)
            out.append(row)
        self.rows = out

    def put(self, x: int, y: int, color: int) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.rows[y][x] = color

    def put_rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            row = self.rows[yy]
            for xx in range(x0, x1):
                row[xx] = color

    def blend_rect(self, x: int, y: int, w: int, h: int, color: int, every: int = 2) -> None:
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            row = self.rows[yy]
            for xx in range(x0, x1):
                if (xx + yy) % every == 0:
                    row[xx] = color

    def blit(self, sprite: Sprite, left: int, top: int, scale: int = 1, row_offsets=None, tint=None) -> None:
        sprite.blit(self, left, top, scale, row_offsets, tint)

    def draw_scroll_markings(self, scroll: float) -> None:
        lay = self.layout
        line_w = max(1, lay.scale // 2)
        dash = 4 * lay.scale
        gap = 5 * lay.scale
        cycle = dash + gap
        phase = int(scroll) % cycle
        for boundary in (lay.road_x + lay.lane_w, lay.road_x + 3 * lay.lane_w):
            for y in range(self.h):
                if (y - phase) % cycle < dash:
                    for k in range(line_w):
                        self.put(boundary + k, y, C["line_white"])

        # Painted arrows were deliberately left out: at terminal cell sizes
        # they read as plus signs, not lane direction.

    def draw_grass_texture(self, scroll: float) -> None:
        """A few tiny flowers/tufts that travel with the verge."""
        lay = self.layout
        spacing = 17 * lay.scale
        phase = int(scroll) % spacing
        for side in (-1, 1):
            for i in range(6):
                gx = lay.road_x - 3 - i * 2 if side < 0 else lay.road_x + lay.road_w + 2 + i * 2
                if not (0 <= gx < self.w):
                    continue
                for base in range(-spacing, self.h + spacing, spacing):
                    gy = base + phase + (hash2d(i, side + 2, 3) % 7)
                    color = (C["flower"] if i % 3 == 0 else C["grass1"]) if (i + base) % 2 else C["grass0"]
                    self.put(gx, gy, color)

    def compose(self, canvas, top: int) -> None:
        rows = self.rows
        half = GLYPHS.half
        w = self.w
        h = self.h
        ch = canvas.ch
        fg = canvas.fg
        bg = canvas.bg
        attr = canvas.attr
        cw = canvas.w
        chh = canvas.h
        for sy in range(0, h - 1, 2):
            y = top + sy // 2
            if y < 0 or y >= chh - 1:
                continue
            base = y * cw
            upper = rows[sy]
            lower = rows[sy + 1]
            for x in range(w):
                i = base + x
                ch[i] = half
                fg[i] = upper[x]
                bg[i] = lower[x]
                attr[i] = 0
