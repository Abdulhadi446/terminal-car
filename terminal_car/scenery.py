"""Roadside scenery that scrolls with the highway."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .constants import C
from .layout import Layout
from .sprites import Sprite, bush_sprite, pine_sprite, rock_sprite, tree_sprite


@dataclass
class SceneryItem:
    sprite: Sprite
    x: int
    y: float
    side: int


class Scenery:
    """Recycled trees, bushes and rocks on both verges."""

    def __init__(self, layout: Layout, seed: int = 7):
        self.rng = random.Random(seed)
        self.layout = layout
        self.items: list[SceneryItem] = []
        self.scroll = 0.0
        self._populate()

    # ------------------------------------------------------------------
    def _verge(self, side: int) -> tuple[int, int]:
        lay = self.layout
        if side < 0:
            return 0, max(0, lay.road_x - 2)
        return min(lay.cols, lay.road_right + 2), lay.cols

    def _tree_for_side(self, side: int) -> tuple[Sprite, int, int]:
        lay = self.layout
        lo, hi = self._verge(side)
        if hi - lo < 4:
            return tree_sprite(0), lo, hi
        roll = self.rng.random()
        if roll < 0.46:
            sprite = tree_sprite(self.rng.randrange(6))
        elif roll < 0.62:
            sprite = pine_sprite(self.rng.randrange(4))
        elif roll < 0.86:
            sprite = bush_sprite(self.rng.randrange(3))
        else:
            sprite = rock_sprite()
        w = sprite.w * lay.scale
        if lo + w > hi:
            span = max(1, hi - lo - w)
            x = lo + self.rng.randrange(span + 1)
        else:
            x = self.rng.randrange(lo, max(lo + 1, hi - w + 1))
        return sprite, x, side

    def _respawn(self, item: SceneryItem, first: bool = False) -> None:
        lay = self.layout
        item.side = -1 if self.rng.random() < 0.5 else 1
        sprite, x, side = self._tree_for_side(item.side)
        item.sprite = sprite
        item.x = x
        item.side = side
        if first:
            item.y = self.rng.uniform(-item.sprite.h * lay.scale, lay.world_half)
        else:
            item.y = -item.sprite.h * lay.scale - self.rng.uniform(0.0, lay.world_half * 0.8)

    def _populate(self) -> None:
        lay = self.layout
        self.items.clear()
        count = max(4, lay.world_half // max(8, 11 * lay.scale))
        for side in (-1, 1):
            for _ in range(count):
                spr, x, s = self._tree_for_side(side)
                y = self.rng.uniform(-spr.h * lay.scale, lay.world_half)
                self.items.append(SceneryItem(spr, x, y, s))
        self.scroll = 0.0

    # ------------------------------------------------------------------
    def reset(self, layout: Layout) -> None:
        self.layout = layout
        self._populate()

    def update(self, dt: float, speed: float) -> None:
        lay = self.layout
        self.scroll += speed * dt
        for item in self.items:
            item.y += speed * dt
            if item.y > lay.world_half + 2:
                self._respawn(item)

    # ------------------------------------------------------------------
    def draw(self, world) -> None:
        lay = self.layout
        for item in self.items:
            if item.y > lay.world_half or item.y + item.sprite.h * lay.scale < 0:
                continue
            left = int(item.x)
            top = int(item.y)
            item.sprite.blit(world, left, top, lay.scale)

        self._draw_posts(world)

    def _draw_posts(self, world) -> None:
        lay = self.layout
        spacing = 13 * lay.scale
        phase = int(self.scroll) % spacing
        pw = max(1, lay.scale)
        ph = max(2, 2 * lay.scale)
        for base in range(-spacing, lay.world_half + spacing, spacing):
            y = base + phase
            for px in (lay.road_x - 2 * lay.scale, lay.road_right + lay.scale):
                if not (0 <= px < lay.cols):
                    continue
                for yy in range(ph):
                    world.put(px, y + yy, C["post"])
                world.put(px, y, C["post_red"])
                if lay.scale > 1:
                    world.put(px + 1, y, C["post_red"])
