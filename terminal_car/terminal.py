"""Terminal canvas, colour management and flicker-free renderer."""

from __future__ import annotations

from typing import Sequence

import curses

from .constants import FONT_3X5
from .utils import to_basic_color, unicode_ok


class Glyphs:
    def __init__(self, fancy: bool):
        self.fancy = fancy
        if fancy:
            self.half = "▀"
            self.full = "█"
            self.shade = "░"
            self.shade2 = "▒"
            self.arrow_l = "←"
            self.arrow_r = "→"
            self.arrow_u = "↑"
            self.arrow_d = "↓"
            self.dot = "·"
            self.dash = "—"
            self.heart = "♥"
            self.bullet = "●"
            self.box_double = ("╔", "╗", "╚", "╝", "═", "║")
            self.box_single = ("┌", "┐", "└", "┘", "─", "│")
            self.box_round = ("╭", "╮", "╰", "╯", "─", "│")
        else:
            self.half = "#"
            self.full = "#"
            self.shade = "."
            self.shade2 = ":"
            self.arrow_l = "<"
            self.arrow_r = ">"
            self.arrow_u = "^"
            self.arrow_d = "v"
            self.dot = "."
            self.dash = "-"
            self.heart = "<3"
            self.bullet = "*"
            self.box_double = ("+", "+", "+", "+", "-", "|")
            self.box_single = ("+", "+", "+", "+", "-", "|")
            self.box_round = ("+", "+", "+", "+", "-", "|")


GLYPHS = Glyphs(unicode_ok())


class Colors:
    """Lazily allocates curses colour pairs for arbitrary fg/bg combos."""

    def __init__(self, color_count: int, pair_count: int, enabled: bool = True):
        self.enabled = enabled and color_count > 0
        self.color_count = color_count
        self.pair_count = max(0, pair_count)
        self._cache: dict[tuple[int, int], int] = {}
        self._next = 1
        if self.enabled:
            try:
                curses.start_color()
            except curses.error:
                pass
            try:
                curses.use_default_colors()
            except curses.error:
                pass
        self._quantize = color_count < 256

    def _map(self, index: int) -> int:
        if self._quantize:
            return to_basic_color(index)
        return index if 0 <= index < self.color_count else 7

    def pair(self, fg: int, bg: int) -> int:
        if not self.enabled:
            return 0
        key = (fg, bg)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        fg2, bg2 = self._map(fg), self._map(bg)
        if self._next >= self.pair_count:
            pair_id = 0
        else:
            pair_id = self._next
            try:
                curses.init_pair(pair_id, fg2, bg2)
                self._next += 1
            except curses.error:
                pair_id = 0
        self._cache[key] = pair_id
        return pair_id


class Canvas:
    """A back buffer of terminal cells."""

    def __init__(self, width: int, height: int):
        self.w = max(1, width)
        self.h = max(1, height)
        n = self.w * self.h
        self.ch = [" "] * n
        self.fg = [252] * n
        self.bg = [233] * n
        self.attr = [0] * n

    def resize(self, width: int, height: int) -> None:
        self.__init__(width, height)

    def _idx(self, x: int, y: int) -> int:
        return y * self.w + x

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def set(self, x: int, y: int, ch: str, fg: int, bg: int, attr: int = 0) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            self.ch[i] = ch
            self.fg[i] = fg
            self.bg[i] = bg
            self.attr[i] = attr

    def set_colors(self, x: int, y: int, fg: int, bg: int, attr: int = 0) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            self.fg[i] = fg
            self.bg[i] = bg
            self.attr[i] = attr

    def get(self, x: int, y: int):
        if not self.inside(x, y):
            return None
        i = y * self.w + x
        return self.ch[i], self.fg[i], self.bg[i], self.attr[i]

    def fill(self, x: int, y: int, w: int, h: int, ch: str, fg: int, bg: int, attr: int = 0) -> None:
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        for row in range(y0, y1):
            base = row * self.w
            for col in range(x0, x1):
                i = base + col
                self.ch[i] = ch
                self.fg[i] = fg
                self.bg[i] = bg
                self.attr[i] = attr

    def fill_bg(self, x: int, y: int, w: int, h: int, bg: int) -> None:
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for row in range(y0, y1):
            base = row * self.w
            for col in range(x0, x1):
                self.bg[base + col] = bg

    def text(
        self,
        x: int,
        y: int,
        string: str,
        fg: int | Sequence[int],
        bg: int | None = None,
        attr: int = 0,
    ) -> int:
        """Draw one-cell-wide text. fg may be a sequence cycled per character."""
        cy = y
        if 0 <= cy < self.h:
            base = cy * self.w
            for idx, char in enumerate(string):
                cx = x + idx
                if 0 <= cx < self.w:
                    i = base + cx
                    self.ch[i] = char
                    if isinstance(fg, int):
                        self.fg[i] = fg
                    else:
                        self.fg[i] = fg[idx % len(fg)]
                    if bg is not None:
                        self.bg[i] = bg
                    self.attr[i] = attr
        return x + len(string)

    def center(self, y: int, string: str, fg: int | Sequence[int], bg: int | None = None, attr: int = 0) -> None:
        x = max(0, (self.w - len(string)) // 2)
        self.text(x, y, string, fg, bg, attr)

    def right(self, y: int, string: str, fg: int, bg: int | None = None, attr: int = 0) -> None:
        x = max(0, self.w - len(string) - 1)
        self.text(x, y, string, fg, bg, attr)

    def box(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        border: int,
        bg: int,
        style: str = "double",
        attr: int = 0,
        shadow: int | None = None,
    ) -> None:
        if w < 2 or h < 2:
            return
        if shadow is not None:
            self.fill(x + 2, y + h, max(0, w), 1, " ", shadow, shadow)
            self.fill(x + w, y + 1, 2, max(0, h), " ", shadow, shadow)
        self.fill(x, y, w, h, " ", 252, bg)
        if style == "double":
            tl, tr, bl, br, hz, vt = GLYPHS.box_double
        elif style == "round":
            tl, tr, bl, br, hz, vt = GLYPHS.box_round
        else:
            tl, tr, bl, br, hz, vt = GLYPHS.box_single
        self.set(x, y, tl, border, bg, attr)
        self.set(x + w - 1, y, tr, border, bg, attr)
        self.set(x, y + h - 1, bl, border, bg, attr)
        self.set(x + w - 1, y + h - 1, br, border, bg, attr)
        for cx in range(x + 1, x + w - 1):
            self.set(cx, y, hz, border, bg, attr)
            self.set(cx, y + h - 1, hz, border, bg, attr)
        for cy in range(y + 1, y + h - 1):
            self.set(x, cy, vt, border, bg, attr)
            self.set(x + w - 1, cy, vt, border, bg, attr)

    def hline(self, x: int, y: int, w: int, fg: int, bg: int | None = None, ch: str = "─") -> None:
        for cx in range(x, x + w):
            if 0 <= cx < self.w and 0 <= y < self.h:
                i = y * self.w + cx
                self.ch[i] = ch
                self.fg[i] = fg
                if bg is not None:
                    self.bg[i] = bg

    def dim(self) -> None:
        """Cheap visual scrim: replace the screen with a dark stipple."""
        for y in range(self.h):
            base = y * self.w
            for x in range(self.w):
                i = base + x
                if (x + y) % 2 == 0:
                    self.ch[i] = GLYPHS.shade
                    self.fg[i] = 234
                else:
                    self.ch[i] = " "
                    self.fg[i] = 233
                self.bg[i] = 233

    def pixel_text_width(self, string: str, scale_x: int = 1, spacing: int = 1) -> int:
        return len(string) * (3 * scale_x + spacing) - spacing if string else 0

    def pixel_text(
        self,
        x: int,
        y: int,
        string: str,
        fg: int | Sequence[int],
        scale_x: int = 1,
        scale_y: int = 1,
        spacing: int = 1,
        shadow: int | None = None,
        bg: int | None = None,
        attr: int = 0,
    ) -> int:
        """Draw block-font text using full-block cells."""
        px = x
        for char_idx, char in enumerate(string.upper()):
            glyph = FONT_3X5.get(char, FONT_3X5["?"])
            color = fg[char_idx % len(fg)] if not isinstance(fg, int) else fg
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit != "1":
                        continue
                    for sy in range(scale_y):
                        for sx in range(scale_x):
                            cx = px + gx * scale_x + sx
                            cy = y + gy * scale_y + sy
                            if shadow is not None:
                                self.set(cx + 1, cy + 1, GLYPHS.full, shadow, bg if bg is not None else 233, attr)
                            self.set(cx, cy, GLYPHS.full, color, bg if bg is not None else 233, attr)
            px += 3 * scale_x + spacing
        return px - spacing if string else x

    def pixel_text_center(
        self,
        y: int,
        string: str,
        fg: int | Sequence[int],
        scale_x: int = 1,
        scale_y: int = 1,
        spacing: int = 1,
        shadow: int | None = None,
        bg: int | None = None,
        attr: int = 0,
    ) -> int:
        width = self.pixel_text_width(string, scale_x, spacing)
        x = max(0, (self.w - width) // 2)
        return self.pixel_text(x, y, string, fg, scale_x, scale_y, spacing, shadow, bg, attr)


class Renderer:
    """Diff-based screen painter. Only changed cells are sent to curses."""

    def __init__(self, screen, colors: Colors):
        self.screen = screen
        self.colors = colors
        self.prev: list[tuple[str, int, int, int]] = []
        self.w = 0
        self.h = 0

    def invalidate(self) -> None:
        self.prev = []
        self.w = 0
        self.h = 0

    def present(self, canvas: Canvas) -> None:
        h, w = self.screen.getmaxyx()
        if (w, h) != (self.w, self.h):
            self.w, self.h = w, h
            self.prev = [("", -1, -1, -1)] * (w * h)
        cw, chh = min(w, canvas.w), min(h, canvas.h)
        prev = self.prev
        for y in range(chh):
            base = y * canvas.w
            pbase = y * w
            for x in range(cw):
                i = base + x
                cell = (canvas.ch[i], canvas.fg[i], canvas.bg[i], canvas.attr[i])
                pi = pbase + x
                if prev[pi] == cell:
                    continue
                prev[pi] = cell
                pair = self.colors.pair(cell[1], cell[2])
                attr = cell[3]
                if pair:
                    attr |= curses.color_pair(pair)
                try:
                    self.screen.addstr(y, x, cell[0], attr)
                except (curses.error, UnicodeEncodeError):
                    pass
        try:
            self.screen.noutrefresh()
            curses.doupdate()
        except curses.error:
            pass
