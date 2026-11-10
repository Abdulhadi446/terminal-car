"""Game entities: player, traffic, power-ups, particles and popups."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .constants import (
    BOOST_TIME,
    LANES,
    MULTIPLIER_TIME,
    NITRO_COST,
    NITRO_DURATION,
    NITRO_MAX,
    NITRO_REGEN,
    ONCOMING_LANES,
    PLAYER_MAX_HEALTH,
    PLAYER_START_LANE,
    SLOWMO_TIME,
    START_HEALTH,
)
from .layout import Layout
from .sprites import Sprite, car_sprite, powerup_sprite
from .utils import approach, clamp


@dataclass
class Player:
    layout: Layout
    lane: int = PLAYER_START_LANE
    target_lane: int = PLAYER_START_LANE
    x: float = 0.0
    health: int = START_HEALTH
    throttle: float = 0.55
    tilt: float = 0.0
    nitro: float = 45.0
    nitro_timer: float = 0.0
    nitro_cooldown: float = 0.0
    boost_timer: float = 0.0
    slow_timer: float = 0.0
    multi_timer: float = 0.0
    shield: bool = False
    invuln: float = 0.0
    recover: float = 0.0
    bob: float = 0.0
    sprite: Sprite = field(default_factory=lambda: car_sprite("sports", "__player__", False, True))

    def __post_init__(self) -> None:
        self.reset(self.layout)

    def reset(self, layout: Layout) -> None:
        self.layout = layout
        self.lane = PLAYER_START_LANE
        self.target_lane = PLAYER_START_LANE
        self.x = layout.lane_center(PLAYER_START_LANE)
        self.health = START_HEALTH
        self.throttle = 0.55
        self.tilt = 0.0
        self.nitro = 45.0
        self.nitro_timer = 0.0
        self.nitro_cooldown = 0.0
        self.boost_timer = 0.0
        self.slow_timer = 0.0
        self.multi_timer = 0.0
        self.shield = False
        self.invuln = 0.0
        self.recover = 0.0
        self.bob = 0.0

    @property
    def width(self) -> int:
        return self.sprite.w * self.layout.scale

    @property
    def height(self) -> int:
        return self.sprite.h * self.layout.scale

    @property
    def top(self) -> float:
        return float(self.layout.player_top_for_throttle(self.throttle))

    @property
    def left(self) -> float:
        return self.x - self.width / 2

    @property
    def right(self) -> float:
        return self.x + self.width / 2

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def oncoming(self) -> bool:
        return self.lane in ONCOMING_LANES

    @property
    def speed_bonus(self) -> float:
        bonus = 1.0
        if self.nitro_timer > 0:
            bonus = max(bonus, 1.5)
        if self.boost_timer > 0:
            bonus = max(bonus, 1.35)
        return bonus

    @property
    def score_multiplier(self) -> float:
        mult = 1.0
        if self.nitro_timer > 0:
            mult += 0.5
        if self.boost_timer > 0:
            mult += 0.5
        if self.multi_timer > 0:
            mult += 1.0
        return mult

    def hitbox(self) -> tuple[float, float, float, float]:
        inset_x = 1.0 * self.layout.scale
        inset_y = 1.0 * self.layout.scale
        return (
            self.left + inset_x,
            self.top + inset_y,
            self.right - inset_x,
            self.bottom - inset_y,
        )

    def steer(self, direction: int) -> None:
        self.target_lane = int(clamp(self.target_lane + direction, 0, LANES - 1))

    def update(self, dt: float) -> None:
        target = self.layout.lane_center(self.target_lane)
        self.x = approach(self.x, target, 15.0, dt)
        if abs(self.x - target) < 0.05:
            self.x = target
        self.tilt = clamp((target - self.x) / max(1.0, self.layout.lane_w * 0.65), -1.0, 1.0)
        self.nitro_cooldown = max(0.0, self.nitro_cooldown - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.recover = max(0.0, self.recover - dt)
        self.bob += dt
        if self.nitro_timer > 0:
            self.nitro_timer = max(0.0, self.nitro_timer - dt)
            if self.nitro_timer == 0:
                self.nitro_cooldown = 0.55
        else:
            need = any((
                self.boost_timer > 0,
                self.slow_timer > 0,
                self.multi_timer > 0,
                self.shield,
            ))
            regen = NITRO_REGEN * (0.55 if need else 1.0)
            self.nitro = min(NITRO_MAX, self.nitro + regen * dt)
        if self.boost_timer > 0:
            self.boost_timer = max(0.0, self.boost_timer - dt)
        if self.slow_timer > 0:
            self.slow_timer = max(0.0, self.slow_timer - dt)
        if self.multi_timer > 0:
            self.multi_timer = max(0.0, self.multi_timer - dt)

    def try_nitro(self) -> bool:
        if self.nitro_timer > 0 or self.nitro_cooldown > 0:
            return False
        if self.nitro < NITRO_COST:
            return False
        self.nitro = max(0.0, self.nitro - NITRO_COST)
        self.nitro_timer = NITRO_DURATION
        return True

    def heal(self) -> bool:
        if self.health >= PLAYER_MAX_HEALTH:
            return False
        self.health += 1
        return True

    def apply_powerup(self, kind: str) -> str:
        if kind == "health":
            if self.heal():
                return "+1 HULL"
            return "FULL HULL"
        if kind == "shield":
            self.shield = True
            return "SHIELD ONLINE"
        if kind == "boost":
            self.boost_timer = max(self.boost_timer, BOOST_TIME)
            self.nitro = min(NITRO_MAX, self.nitro + 25.0)
            return "BOOST"
        if kind == "slow":
            self.slow_timer = max(self.slow_timer, SLOWMO_TIME)
            return "SLOW-MO"
        if kind == "multi":
            self.multi_timer = max(self.multi_timer, MULTIPLIER_TIME)
            return "x2 SCORE"
        return kind


@dataclass
class TrafficCar:
    lane: int
    y: float
    palette_name: str
    kind: str
    oncoming: bool
    speed_jitter: float
    sprite: Sprite
    lane_w: int
    prev_y: float = 0.0
    awarded: bool = False
    hit: bool = False
    wobble: float = 0.0

    def __post_init__(self) -> None:
        self.prev_y = self.y
        self.wobble = random.random() * 6.28

    @property
    def facing_down(self) -> bool:
        return self.oncoming

    @property
    def screen_speed(self) -> float:
        # Relative magnification is applied by the game's speed base.
        return self.speed_jitter

    def left_for(self, layout: Layout) -> float:
        w = self.sprite.w * layout.scale
        return layout.lane_center(self.lane) - w / 2

    @property
    def scale_width(self) -> int:
        return self.sprite.w

    def hitbox(self, layout: Layout) -> tuple[float, float, float, float]:
        w = self.sprite.w * layout.scale
        h = self.sprite.h * layout.scale
        left = layout.lane_center(self.lane) - w / 2 + layout.scale
        top = self.y + layout.scale
        return (left, top, left + w - 2 * layout.scale, top + h - 2 * layout.scale)


@dataclass
class PowerUp:
    kind: str
    lane: int
    y: float
    bob_phase: float
    age: float = 0.0
    collected: bool = False
    sprite: Sprite = field(init=False)

    def __post_init__(self) -> None:
        self.sprite = powerup_sprite(self.kind)

    def x_for(self, layout: Layout) -> float:
        return layout.lane_center(self.lane)

    def hitbox(self, layout: Layout) -> tuple[float, float, float, float]:
        w = 9 * layout.scale
        h = 9 * layout.scale
        x = self.x_for(layout) - w / 2
        y = self.y
        return (x, y, x + w, y + h)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: int
    size: int = 1
    drag: float = 0.0
    gravity: float = 0.0
    fade: bool = False

    def update(self, dt: float) -> bool:
        self.life -= dt
        if self.life <= 0:
            return False
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.drag:
            factor = max(0.0, 1.0 - self.drag * dt)
            self.vx *= factor
            self.vy *= factor
        self.vy += self.gravity * dt
        return True


@dataclass
class Popup:
    text: str
    x: float
    y: float
    color: int
    life: float = 1.2
    max_life: float = 1.2
    vy: float = -7.0
    bg: int = 233
    bold: bool = True

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.y += self.vy * dt
        self.vy *= max(0.0, 1.0 - 2.0 * dt)
        return self.life > 0

    @property
    def alpha_phase(self) -> float:
        t = clamp(self.life / self.max_life, 0.0, 1.0)
        if t > 0.75:
            return (1.0 - t) / 0.25
        return t / 0.75


@dataclass
class SkidMark:
    x: float
    y: float
    life: float = 0.8
    max_life: float = 0.8
    color: int = 235
