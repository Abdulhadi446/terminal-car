"""Small helpers shared across the game."""

from __future__ import annotations

import math
import os
import sys
from typing import Iterable


def clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def approach(current: float, target: float, rate: float, dt: float) -> float:
    """Exponential ease toward target (frame-rate independent)."""
    return target + (current - target) * math.exp(-rate * dt)


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def fmt_dist(meters: float) -> str:
    km = meters / 1000.0
    if km >= 100:
        return f"{km:.0f} km"
    if km >= 10:
        return f"{km:.1f} km"
    return f"{km:.2f} km"


def fmt_score(score: float) -> str:
    return f"{int(score):07d}"


def pulse(t: float, speed: float = 1.0) -> float:
    """0..1 triangle wave."""
    x = (t * speed) % 1.0
    return x * 2 if x < 0.5 else (1.0 - x) * 2


def wrap(text: str, width: int) -> list[str]:
    if width <= 0:
        return [text]
    out: list[str] = []
    line = ""
    for word in text.split(" "):
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= width:
            line += " " + word
        else:
            out.append(line)
            line = word
    if line:
        out.append(line)
    return out


def hash2d(x: int, y: int, seed: int = 0) -> int:
    """Deterministic, cheap integer hash with decent low-bit behaviour."""
    h = (x * 374761393 + y * 668265263 + seed * 1274126177) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return (h ^ (h >> 16)) & 0xFFFFFFFF


def pick_weighted(rng, items: Iterable[tuple[object, float]]):
    """Pick from ((value, weight), ...) using random.Random."""
    items = list(items)
    total = sum(w for _, w in items)
    if total <= 0:
        return items[0][0]
    roll = rng.uniform(0, total)
    for value, weight in items:
        roll -= weight
        if roll <= 0:
            return value
    return items[-1][0]


# ---------------------------------------------------------------------------
# 256-colour -> basic terminal colour fallback
# ---------------------------------------------------------------------------
_BASIC_XTERM = {
    "black": 0, "red": 1, "green": 2, "yellow": 3, "blue": 4,
    "magenta": 5, "cyan": 6, "white": 7,
}


def _cube_value(v: int) -> int:
    return 0 if v == 0 else 55 + v * 40


def xterm_rgb(index: int) -> tuple[int, int, int]:
    if index < 16:
        base = [
            (0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0),
            (0, 0, 128), (128, 0, 128), (0, 128, 128), (192, 192, 192),
            (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0),
            (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
        ]
        return base[index]
    if index < 232:
        n = index - 16
        r, g, b = n // 36, (n // 6) % 6, n % 6
        return _cube_value(r), _cube_value(g), _cube_value(b)
    level = 8 + (index - 232) * 10
    return level, level, level


def to_basic_color(index: int) -> int:
    """Map an xterm-256 colour to the nearest bright basic ANSI colour."""
    r, g, b = xterm_rgb(index)
    palette = {
        0: (0, 0, 0), 1: (170, 0, 0), 2: (0, 170, 0), 3: (170, 85, 0),
        4: (0, 0, 170), 5: (170, 0, 170), 6: (0, 170, 170),
        7: (200, 200, 200), 8: (90, 90, 90), 9: (255, 85, 85),
        10: (85, 255, 85), 11: (255, 255, 85), 12: (85, 85, 255),
        13: (255, 85, 255), 14: (85, 255, 255), 15: (255, 255, 255),
    }
    best, best_d = 7, 1e18
    for code, (pr, pg, pb) in palette.items():
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_d:
            best, best_d = code, d
    return best


def unicode_ok() -> bool:
    """Best-effort detection of a UTF-8 capable terminal."""
    if os.environ.get("TERMINAL_RUSH_ASCII"):
        return False
    enc = (getattr(sys.stdout, "encoding", None) or "").lower().replace("-", "")
    if "utf" not in enc:
        return False
    return True
