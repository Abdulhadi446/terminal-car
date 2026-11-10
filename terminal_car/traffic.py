"""Traffic simulation: spawning, relative motion and fair lane selection."""

from __future__ import annotations

import random

from .constants import CAR_PALETTES, C, FORWARD_LANES, LANES
from .entities import TrafficCar
from .layout import Layout
from .sprites import car_sprite
from .utils import clamp, pick_weighted

TRAFFIC_KINDS = (
    ("sedan", 28.0),
    ("hatch", 20.0),
    ("sports", 13.0),
    ("taxi", 11.0),
    ("van", 13.0),
    ("truck", 7.0),
    ("bus", 4.0),
)

PALETTE_NAMES = tuple(CAR_PALETTES.keys())


class TrafficManager:
    def __init__(self, layout: Layout, seed: int | None = None):
        self.rng = random.Random(seed)
        self.layout = layout
        self.cars: list[TrafficCar] = []
        self.timer = 0.9
        self.time = 0.0
        self.spawn_count = 0

    # ------------------------------------------------------------------
    def reset(self, layout: Layout | None = None) -> None:
        if layout is not None:
            self.layout = layout
        self.cars.clear()
        self.timer = 0.9
        self.time = 0.0
        self.spawn_count = 0

    def discard(self, car: TrafficCar) -> None:
        try:
            self.cars.remove(car)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    def _entry_lanes(self) -> set[int]:
        lay = self.layout
        band = 21 * lay.scale
        return {
            car.lane
            for car in self.cars
            if car.y < band and car.y + car.sprite.h * lay.scale > -30 * lay.scale
        }

    def _lane_clear_for_spawn(self, lane: int) -> bool:
        lay = self.layout
        for car in self.cars:
            if car.lane != lane:
                continue
            if car.y < 19 * lay.scale:
                return False
        return True

    def _choose_lane(self, taken: set[int]) -> int | None:
        choices: list[tuple[int, float]] = []
        for lane in range(LANES):
            if lane in taken or not self._lane_clear_for_spawn(lane):
                continue
            weight = 1.15 if lane in FORWARD_LANES else 0.92
            choices.append((lane, weight))
        if not choices:
            return None
        return pick_weighted(self.rng, choices)

    def spawn_wave(self, difficulty: float) -> None:
        entry = self._entry_lanes()
        # Keep two lanes open at the top of the road so a player always has
        # an escape route when the next wave arrives.
        if len(entry) >= LANES - 2:
            return
        taken: set[int] = set()
        max_cars = 1
        if difficulty > 0.55 and self.rng.random() < 0.12 + difficulty * 0.12:
            max_cars = 2

        for _ in range(max_cars):
            if len(entry | taken) >= LANES - 2:
                break
            lane = self._choose_lane(taken)
            if lane is None:
                break
            taken.add(lane)
            self._spawn(lane)
            entry.add(lane)
            if self.rng.random() < 0.28:
                break
        if taken:
            self.spawn_count += 1

    def _spawn(self, lane: int) -> TrafficCar:
        lay = self.layout
        kind = pick_weighted(self.rng, TRAFFIC_KINDS)
        palette = self.rng.choice(PALETTE_NAMES)
        oncoming = lane not in FORWARD_LANES
        sprite = car_sprite(kind, palette, oncoming)
        y = -sprite.h * lay.scale - self.rng.uniform(0, 8 * lay.scale)
        car = TrafficCar(
            lane=lane,
            y=y,
            palette_name=palette,
            kind=kind,
            oncoming=oncoming,
            speed_jitter=self.rng.random(),
            sprite=sprite,
            lane_w=lay.lane_w,
        )
        self.cars.append(car)
        return car

    # ------------------------------------------------------------------
    def update(
        self,
        dt: float,
        scroll: float,
        difficulty: float,
        slow_factor: float = 1.0,
        spawning: bool = True,
    ) -> None:
        lay = self.layout
        self.time += dt
        limit = lay.world_half + 2
        alive: list[TrafficCar] = []
        for car in self.cars:
            car.prev_y = car.y
            jitter = car.speed_jitter
            if car.oncoming:
                relative = scroll * (1.18 + 0.30 * jitter) + 3.0 * lay.scale
            else:
                relative = scroll * (0.34 + 0.24 * jitter)
            car.y += relative * slow_factor * dt
            if car.y <= limit:
                alive.append(car)
        self.cars = alive

        if not spawning:
            return
        self.timer -= dt
        if self.timer <= 0:
            self.spawn_wave(difficulty)
            interval = (1.8 - 0.65 * clamp(difficulty, 0.0, 1.0)) * self.rng.uniform(0.82, 1.22)
            self.timer = max(0.62, interval)

    # ------------------------------------------------------------------
    def draw(self, world) -> None:
        lay = self.layout
        for car in self.cars:
            if car.y > lay.world_half or car.y + car.sprite.h * lay.scale < 0:
                continue
            left = int(round(car.left_for(lay)))
            top = int(round(car.y))
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                car.sprite.blit(world, left + ox, top + oy, lay.scale, tint=C["shadow"])
            car.sprite.blit(world, left + 2, top + 2, lay.scale, tint=C["shadow"])
            car.sprite.blit(world, left, top, lay.scale)
