"""Pixel-art sprites rendered with terminal half-block colours."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .constants import CAR_PALETTES, FONT_3X5, PLAYER_PALETTE, POWERUP_STYLE
from .utils import hash2d

TRANSPARENT = -1


@dataclass(frozen=True)
class Sprite:
    rows: tuple[tuple[int, ...], ...]
    w: int
    h: int

    def blit(
        self,
        world,
        left: int,
        top: int,
        scale: int = 1,
        row_offsets: tuple[int, ...] | None = None,
        tint: int | None = None,
        dy: int = 0,
        dx: int = 0,
    ) -> None:
        """Draw into a World. Transparent pixels are skipped."""
        for sy, row in enumerate(self.rows):
            offset = row_offsets[sy] if row_offsets and sy < len(row_offsets) else 0
            py = top + sy * scale + dy
            for sx, color in enumerate(row):
                if color == TRANSPARENT:
                    continue
                c = tint if tint is not None else color
                px = left + sx * scale + offset + dx
                for yy in range(scale):
                    for xx in range(scale):
                        world.put(px + xx, py + yy, c)


# ---------------------------------------------------------------------------
# Car templates. '.' is transparent. Width is checked at import time.
# ---------------------------------------------------------------------------
_TEMPLATES: dict[str, tuple[str, ...]] = {
    "sedan": (
        "..H...H..",
        ".BBBBBBB.",
        "BBBBBBBBB",
        "TBWWWWWBT",
        "MBBBBBBBM",
        "BBBBBBBBB",
        "BBWWWWWBB",
        "TBBBBBBBT",
        ".BBBBBBB.",
        ".BBBBBBB.",
        "..R...R..",
    ),
    "hatch": (
        "..H...H..",
        ".BBBBBBB.",
        "BBBBBBBBB",
        "TBWWWWWBT",
        "MBBBBBBBM",
        "BBWWWWWBB",
        ".BBBBBBB.",
        "TBBBBBBBT",
        ".BBBBBBB.",
        "..R...R..",
    ),
    "sports": (
        "...H.H...",
        "..BBBBB..",
        ".BBBBBBB.",
        "TBWWWWWBT",
        "MBBBBBBBM",
        "BBBBBBBBB",
        "BBWWWWWBB",
        "TBBBBBBBT",
        ".BBBBBBB.",
        "..BBBBB..",
        ".R.....R.",
    ),
    "van": (
        "..H...H..",
        ".BBBBBBB.",
        "BBBBBBBBB",
        "TBWWWWWBT",
        "MBBBBBBBM",
        "BBBBBBBBB",
        "BBBBBBBBB",
        "BBBBBBBBB",
        "BBBBBBBBB",
        "TBBBBBBBT",
        ".BBBBBBB.",
        ".BBBBBBB.",
        "..R...R..",
    ),
    "taxi": (
        "..H...H..",
        ".BBBBBBB.",
        "BBBBBBBBB",
        "TBWWWWWBT",
        "MBBNNNBBM",
        "BBBBBBBBB",
        "BBWWWWWBB",
        "TBBBBBBBT",
        ".BBBBBBB.",
        ".BBBBBBB.",
        "..R...R..",
    ),
    "truck": (
        "..H...H..",
        ".BBBBBBB.",
        "BBBBBBBBB",
        "TBWWWWWBT",
        "MBBBBBBBM",
        "BBBBBBBBB",
        "BBBBBBBBB",
        ".SSSSSSS.",
        "SCCCCCCCS",
        "SCCCCCCCS",
        "SCCCCCCCS",
        "SCCCCCCCS",
        "SCCCCCCCS",
        ".SSSSSSS.",
        "..R...R..",
    ),
    "bus": (
        "..H...H..",
        ".BBBBBBB.",
        "BBBBBBBBB",
        "TBWWWWWBT",
        "BBBBBBBBB",
        "BWWWWWWWB",
        "BWWWWWWWB",
        "BWWWWWWWB",
        "BWWWWWWWB",
        "BWWWWWWWB",
        "BWWWWWWWB",
        "BBBBBBBBB",
        "TBBBBBBBT",
        ".BBBBBBB.",
        "..R...R..",
    ),
}

for _name, _rows in _TEMPLATES.items():
    _w = len(_rows[0])
    assert all(len(r) == _w for r in _rows), f"bad sprite width for {_name}"


def _palette_map(palette: dict, stripe: int | None = None) -> dict[str, int]:
    body = palette["body"]
    dark = palette["dark"]
    light = palette["light"]
    window = palette["window"]
    return {
        "B": body,
        "D": dark,
        "L": light,
        "W": window,
        "M": dark,
        "T": 232,
        "H": palette.get("headlight", 227),
        "R": palette.get("taillight", 196),
        "N": palette.get("sign", 231),
        "A": stripe if stripe is not None else palette.get("stripe", light),
        "C": dark,
        "S": light,
    }


@lru_cache(maxsize=256)
def car_sprite(kind: str, palette_name: str, facing_down: bool, stripe: bool = False) -> Sprite:
    rows = _TEMPLATES.get(kind, _TEMPLATES["sedan"])
    if palette_name == "__player__":
        palette = PLAYER_PALETTE
        default_stripe = PLAYER_PALETTE["stripe"]
    else:
        palette = CAR_PALETTES.get(palette_name, CAR_PALETTES["silver"])
        default_stripe = palette["light"]
    mapping = _palette_map(palette, default_stripe if stripe else None)

    colors: list[tuple[int, ...]] = []
    for row in rows:
        vals: list[int] = []
        for x, ch in enumerate(row):
            if ch == ".":
                vals.append(TRANSPARENT)
                continue
            color = mapping.get(ch, palette["body"])
            if stripe and ch == "B" and x == 4:
                color = default_stripe
            vals.append(color)
        colors.append(tuple(vals))
    if facing_down:
        colors.reverse()
    return Sprite(tuple(colors), len(rows[0]), len(rows))


def _scenery(rows: tuple[str, ...], mapping: dict[str, int]) -> Sprite:
    colors = tuple(
        tuple(TRANSPARENT if ch == "." else mapping[ch] for ch in row) for row in rows
    )
    return Sprite(colors, len(rows[0]), len(rows))


_TREE_ROUND = (
    "...GGG...",
    ".GGGGGGG.",
    "GGGGLGGGG",
    "GGGGGGGGG",
    "GGGLGGGGG",
    ".GGGGGGG.",
    "..GGGGG..",
    "....T....",
    "....T....",
    "...TTT...",
)
_TREE_PINE = (
    "....G....",
    "...GGG...",
    "..GGGGG..",
    "...GGG...",
    "..GGGGG..",
    ".GGGGGGG.",
    "GGGGGGGGG",
    "..GGGGG..",
    "....T....",
    "....T....",
)
_BUSH = (
    "..GGG..",
    ".GGGGG.",
    "GGGLGGG",
    ".GGGGG.",
    "..GGG..",
)
_ROCK = (
    ".RRR.",
    "RRRRR",
    ".RRR.",
)
_POWERUP = (
    ".EEEEEEE.",
    "EFFFFFFFE",
    "EFFFFFFFE",
    "EFFFFFFFE",
    "EFFFFFFFE",
    "EFFFFFFFE",
    "EFFFFFFFE",
    "EFFFFFFFE",
    ".EEEEEEE.",
)


@lru_cache(maxsize=8)
def tree_sprite(variant: int = 0) -> Sprite:
    mapping = {
        "G": 28 if variant % 2 == 0 else 34,
        "L": 46,
        "T": 94,
    }
    return _scenery(_TREE_ROUND if variant % 3 else _TREE_PINE, mapping)


@lru_cache(maxsize=8)
def pine_sprite(variant: int = 0) -> Sprite:
    mapping = {"G": 22 if variant % 2 == 0 else 28, "L": 34, "T": 94}
    return _scenery(_TREE_PINE, mapping)


@lru_cache(maxsize=4)
def bush_sprite(variant: int = 0) -> Sprite:
    mapping = {"G": 28 if variant % 2 == 0 else 34, "L": 40}
    return _scenery(_BUSH, mapping)


@lru_cache(maxsize=1)
def rock_sprite() -> Sprite:
    mapping = {"R": 243}
    return _scenery(_ROCK, mapping)


def _blank_tile(style: dict) -> list[list[int]]:
    fill, edge = style["fill"], style["edge"]
    rows: list[list[int]] = []
    for y in range(9):
        row: list[int] = []
        for x in range(9):
            if (x in (0, 8)) or (y in (0, 8)):
                row.append(edge)
            elif (x in (1, 7)) and (y in (1, 7)):
                row.append(edge)
            else:
                row.append(fill)
        rows.append(row)
    return rows


@lru_cache(maxsize=8)
def powerup_sprite(kind: str) -> Sprite:
    style = POWERUP_STYLE[kind]
    rows = _blank_tile(style)
    icon = style["icon"]

    def put(x: int, y: int, color: int = icon) -> None:
        if 0 <= x < 9 and 0 <= y < 9:
            rows[y][x] = color

    if kind == "health":
        for y in range(2, 7):
            put(4, y)
        for x in range(2, 7):
            put(x, 4)
        put(4, 2, 231)
    elif kind == "shield":
        for x in range(2, 7):
            put(x, 2)
        for y in range(3, 7):
            put(1, y)
            put(7, y)
        for x in range(2, 7):
            put(x, 7)
        put(4, 7, TRANSPARENT)
        for x in range(3, 6):
            put(x, 3, style["fill"])
        put(3, 3, 231)
        put(4, 3, 231)
    elif kind == "boost":
        bolt = (
            "...II.",
            "..II..",
            ".II...",
            "IIIII.",
            "..II..",
            ".II...",
            "II....",
        )
        for y, line in enumerate(bolt):
            for x, ch in enumerate(line):
                if ch == "I":
                    put(x + 2, y + 1, style["edge"] if y % 2 else 255)
        put(3, 2, 255)
    elif kind == "slow":
        hourglass = (
            "IIIII",
            ".III.",
            "..I..",
            ".III.",
            "IIIII",
        )
        for y, line in enumerate(hourglass):
            for x, ch in enumerate(line):
                if ch == "I":
                    put(x + 2, y + 2, 231)
        put(2, 2, icon)
        put(6, 2, icon)
    elif kind == "multi":
        glyph_x = FONT_3X5["x"]
        glyph_2 = FONT_3X5["2"]
        for y, line in enumerate(glyph_x):
            for x, ch in enumerate(line):
                if ch == "1":
                    put(x + 1, y + 2, icon)
        for y, line in enumerate(glyph_2):
            for x, ch in enumerate(line):
                if ch == "1":
                    put(x + 5, y + 2, icon)

    return Sprite(tuple(tuple(row) for row in rows), 9, 9)


# ---------------------------------------------------------------------------
# Scenery decoration colours
# ---------------------------------------------------------------------------
FLOWER_COLORS = (227, 255, 205, 51)


def grass_tuft_color(x: int, y: int) -> int:
    n = hash2d(x, y, 7) % 100
    if n < 12:
        return 34
    if n < 22:
        return 28
    return 22
