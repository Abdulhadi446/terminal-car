"""Responsive layout math."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import LANES, MIN_COLS, MIN_ROWS
from .utils import clamp


@dataclass(frozen=True)
class Layout:
    cols: int
    rows: int
    scale: int
    lane_w: int
    road_w: int
    road_x: int
    top: int = 3

    @property
    def footer(self) -> int:
        return self.rows - 1

    @property
    def world_rows(self) -> int:
        return self.rows - 4

    @property
    def world_half(self) -> int:
        return self.world_rows * 2

    @property
    def world_x(self) -> int:
        return 0

    @property
    def road_right(self) -> int:
        return self.road_x + self.road_w

    @property
    def speed_scale(self) -> float:
        raw = self.world_half / (40.0 * self.scale)
        return self.scale * clamp(raw, 0.7, 1.9)

    def lane_center(self, lane: int) -> float:
        return self.road_x + (lane + 0.5) * self.lane_w

    def lane_at(self, x: float) -> int:
        lane = int((x - self.road_x) // self.lane_w)
        return max(0, min(LANES - 1, lane))

    @property
    def center_x(self) -> float:
        return self.road_x + self.road_w / 2

    @property
    def player_top(self) -> int:
        """Default player sprite top in world half-row coordinates."""
        return self.world_half - 2 - (11 * self.scale)

    def player_top_for_throttle(self, throttle: float) -> int:
        lift = int(round((throttle - 0.55) * 4 * self.scale))
        return max(6 * self.scale, self.player_top - lift)


def make_layout(cols: int, rows: int) -> Layout | None:
    if cols < MIN_COLS or rows < MIN_ROWS:
        return None
    scale = 2 if cols >= 160 and rows >= 36 else 1
    lane_w = int(clamp((cols - 12) // (LANES * scale), 10, 20)) * scale
    road_w = lane_w * LANES
    road_x = (cols - road_w) // 2
    return Layout(cols=cols, rows=rows, scale=scale, lane_w=lane_w, road_w=road_w, road_x=road_x)
