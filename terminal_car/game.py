"""Core game state, simulation, scoring and effects for Terminal Rush."""

from __future__ import annotations

import math
import random
from pathlib import Path

from .constants import (
    BASE_SCROLL,
    C,
    COUNTDOWN_TIME,
    DYING_TIME,
    LANES,
    MAX_SCROLL,
    NEAR_MISS_BASE,
    NEAR_MISS_CHAIN_WINDOW,
    NEAR_MISS_MAX,
    NEAR_MISS_NITRO,
    NEAR_MISS_STEP,
    NEAR_MISS_THRESHOLD,
    NITRO_COST,
    NITRO_MAX,
    ONCOMING_LANES,
    PLAYER_MAX_HEALTH,
    POWERUP_LIFETIME,
    POWERUP_SPAWN_MAX,
    POWERUP_SPAWN_MIN,
    SCORE_PER_KMH,
    SCORE_SURVIVAL,
    SCROLL_RAMP_SECONDS,
    SLOWMO_TIME,
)
from .entities import Particle, Player, Popup, PowerUp
from .layout import Layout
from .scenery import Scenery
from .storage import save_stats, record_run
from .traffic import TrafficManager
from .utils import clamp, fmt_score, lerp, pulse
from .world import Backdrop, World

MENU = "menu"
COUNTDOWN = "countdown"
PLAYING = "playing"
PAUSED = "paused"
DYING = "dying"
GAMEOVER = "gameover"
EXIT = "exit"

ACTIVE_MODES = (COUNTDOWN, PLAYING, PAUSED, DYING, GAMEOVER)

POWERUP_KINDS = ("health", "shield", "boost", "slow", "multi")


class Game:
    """Owns the highway simulation and the run lifecycle."""

    def __init__(
        self,
        layout: Layout,
        stats: dict | None = None,
        stats_path: Path | None = None,
        seed: int | None = None,
        persist: bool = True,
        demo: bool = False,
    ):
        self.layout = layout
        self.stats = stats if stats is not None else {}
        self.stats_path = stats_path
        self.persist = persist
        self.demo = demo
        self.rng = random.Random(seed)
        self.backdrop = Backdrop(layout)
        self.world = World(layout, self.backdrop)
        self.player = Player(layout)
        self.traffic = TrafficManager(layout, seed)
        self.scenery = Scenery(layout, seed or 7)

        self.mode = MENU
        self.ui_time = 0.0
        self.menu_time = 0.0
        self.countdown = COUNTDOWN_TIME
        self.dying_timer = 0.0
        self.gameover_time = 0.0

        self.score = 0.0
        self.distance_m = 0.0
        self.run_time = 0.0
        self.final_score = 0
        self.final_distance = 0.0
        self.final_time = 0.0
        self.new_best = False

        self.scroll = BASE_SCROLL * layout.speed_scale
        self.scroll_pos = 0.0
        self.speed_kmh = 0.0
        self.difficulty = 0.0

        self.powerups: list[PowerUp] = []
        self.particles: list[Particle] = []
        self.popups: list[Popup] = []
        self.powerup_timer = 6.0

        self.combo = 0
        self.combo_timer = 0.0
        self.last_near = -99.0
        self.demo_timer = 0.0
        self.demo_reaction = 0.0
        self.demo_pending_lane: int | None = None

        self.flash_timer = 0.0
        self.flash_duration = 0.5
        self.flash_color = C["accent"]
        self.flash_strength = 1
        self.shake_timer = 0.0
        self.shake_duration = 0.0
        self.shake_strength = 0.0

        self.exhaust_acc = 0.0
        self.status = ""
        self._enter_menu(first=True)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @property
    def best_score(self) -> int:
        return int(self.stats.get("score", 0))

    @property
    def best_distance(self) -> float:
        return float(self.stats.get("distance_m", 0.0))

    @property
    def best_time(self) -> float:
        return float(self.stats.get("time", 0.0))

    def _clear_effects(self) -> None:
        self.particles.clear()
        self.popups.clear()
        self.powerups.clear()
        self.flash_timer = 0.0
        self.shake_timer = 0.0
        self.exhaust_acc = 0.0
        self.combo = 0
        self.combo_timer = 0.0
        self.last_near = -99.0

    def _enter_menu(self, first: bool = False) -> None:
        self.mode = MENU
        self.menu_time = 0.0
        self.countdown = COUNTDOWN_TIME
        self.player.reset(self.layout)
        self.traffic.reset(self.layout)
        self.scenery.reset(self.layout)
        self._clear_effects()
        self.score = 0.0
        self.distance_m = 0.0
        self.run_time = 0.0
        self.final_score = 0
        self.final_distance = 0.0
        self.final_time = 0.0
        self.new_best = False
        self.scroll = BASE_SCROLL * self.layout.speed_scale * 0.72
        self.speed_kmh = 0.0
        self.traffic.timer = 0.15 if not first else 0.8

    def enter_menu(self) -> None:
        self._enter_menu()

    def start_run(self) -> None:
        self.player.reset(self.layout)
        self.traffic.reset(self.layout)
        self.scenery.reset(self.layout)
        self.world.reset()
        self._clear_effects()
        self.score = 0.0
        self.distance_m = 0.0
        self.run_time = 0.0
        self.final_score = 0
        self.final_distance = 0.0
        self.final_time = 0.0
        self.new_best = False
        self.countdown = COUNTDOWN_TIME
        self.scroll = BASE_SCROLL * self.layout.speed_scale * 0.45
        self.speed_kmh = 0.0
        self.difficulty = 0.0
        self.demo_timer = 0.0
        self.demo_reaction = 0.0
        self.demo_pending_lane = None
        self.traffic.timer = 0.38
        self.powerup_timer = self.rng.uniform(POWERUP_SPAWN_MIN * 0.7, POWERUP_SPAWN_MIN)
        self.mode = COUNTDOWN
        self._popup("ENGINE READY", self.player.x, self._popup_y(), C["accent"], life=1.0)

    def _demo_drive(self, dt: float) -> None:
        """Drive decisively, with a short reaction delay between lane changes."""
        if self.demo_pending_lane is not None:
            self.demo_reaction -= dt
            if self.demo_reaction <= 0:
                direction = 1 if self.demo_pending_lane > self.player.target_lane else -1
                self.player.steer(direction)
                self.demo_pending_lane = None
                self.demo_timer = 0.12
            return

        self.demo_timer -= dt
        if self.demo_timer <= 0:
            self.demo_timer = 0.12
            lay = self.layout
            horizon = self.player.top + 34 * lay.scale
            lane_scores: list[tuple[float, int]] = []
            for lane in range(LANES):
                nearest = horizon + 24 * lay.scale
                for car in self.traffic.cars:
                    if car.lane != lane:
                        continue
                    distance = self.player.top - car.y
                    if -8 * lay.scale <= distance <= 44 * lay.scale:
                        nearest = min(nearest, distance)
                score = nearest - abs(lane - self.player.target_lane) * 3 * lay.scale
                lane_scores.append((score, lane))
            _, best_lane = max(lane_scores)
            if best_lane != self.player.target_lane:
                self.demo_pending_lane = best_lane
                self.demo_reaction = 0.25
            self.player.throttle = 0.72

        if self.player.nitro >= NITRO_COST and self.player.nitro_timer <= 0:
            self.player.try_nitro()

    def _quit(self) -> None:
        self.save_on_exit()
        self.mode = EXIT

    def save_on_exit(self) -> bool:
        """Best-effort save if the run is abandoned in progress."""
        if not self.persist:
            return False
        if self.mode not in (COUNTDOWN, PLAYING, PAUSED, DYING):
            return False
        score = int(self.score)
        changed = False
        if score > self.best_score:
            self.stats["score"] = score
            changed = True
        if self.distance_m > self.best_distance:
            self.stats["distance_m"] = float(self.distance_m)
            changed = True
        if self.run_time > self.best_time:
            self.stats["time"] = float(self.run_time)
            changed = True
        if changed:
            save_stats(self.stats, self.stats_path)
        return changed

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_key(self, key: str) -> bool:
        """Handle a normalised key. Returns False when the program should quit."""
        if key in ("q", "quit"):
            self._quit()
            return False
        if self.mode == MENU:
            if key in ("enter", "space", "start"):
                self.start_run()
            elif key == "escape":
                self._quit()
                return False
        elif self.mode == COUNTDOWN:
            if key in ("space", "enter"):
                self.countdown = 0.0
        elif self.mode == PLAYING:
            if key in ("left", "a"):
                self.player.steer(-1)
            elif key in ("right", "d"):
                self.player.steer(1)
            elif key in ("up", "w"):
                self.player.throttle = clamp(self.player.throttle + 0.12, 0.1, 1.0)
            elif key in ("down", "s"):
                self.player.throttle = clamp(self.player.throttle - 0.12, 0.1, 1.0)
            elif key == "space":
                if self.player.try_nitro():
                    self.flash(C["accent2"], 0.26, 1)
                    self.shake(0.18, 0.8)
                    for _ in range(10):
                        self._spark(self.player.x, self.player.bottom, C["accent2"], speed=9.0)
                elif self.player.nitro_timer > 0:
                    self._popup("NITRO ACTIVE", self.player.x, self._popup_y(), C["accent2"], life=0.55)
                elif self.player.nitro_cooldown > 0:
                    self._popup("NITRO RECHARGING", self.player.x, self._popup_y(), C["dim"], life=0.55)
                else:
                    self._popup("LOW NITRO", self.player.x, self._popup_y(), C["dim"], life=0.55)
            elif key in ("p", "escape"):
                self.mode = PAUSED
            elif key == "r":
                self.start_run()
        elif self.mode == PAUSED:
            if key in ("p", "escape", "space", "enter"):
                self.mode = PLAYING
            elif key == "r":
                self.start_run()
            elif key in ("m", "backspace"):
                self._enter_menu()
        elif self.mode == DYING:
            pass
        elif self.mode == GAMEOVER:
            if key in ("r", "space"):
                self.start_run()
            elif key in ("enter", "m", "escape"):
                self._enter_menu()
        return True

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def relayout(self, layout: Layout) -> None:
        """Rebuild rendering/simulation objects after a terminal resize."""
        if layout == self.layout:
            return
        was_active = self.mode in (COUNTDOWN, PLAYING, PAUSED, DYING, GAMEOVER)
        self.layout = layout
        self.backdrop = Backdrop(layout)
        self.world = World(layout, self.backdrop)
        self.player.layout = layout
        self.player.x = layout.lane_center(self.player.target_lane)
        self.scenery.reset(layout)
        self.traffic.reset(layout)
        self.traffic.timer = 0.5
        self.powerups.clear()
        self.particles.clear()
        self.popups.clear()
        self.scroll_pos = 0.0
        if not was_active:
            self.traffic.timer = 0.8
        if self.mode == GAMEOVER:
            self.traffic.timer = 999.0

    def _scroll_speed(self) -> float:
        progress = clamp(self.run_time / SCROLL_RAMP_SECONDS, 0.0, 1.0)
        base = lerp(BASE_SCROLL, MAX_SCROLL, progress)
        throttle = 0.70 + 0.55 * self.player.throttle
        return base * self.layout.speed_scale * throttle * self.player.speed_bonus

    def _popup_y(self) -> float:
        return self.layout.top + self.player.top / 2.0 - 1.0

    def update(self, dt: float) -> None:
        self.ui_time += dt
        self._tick_effects(dt)
        if self.mode == MENU:
            self._update_menu(dt)
        elif self.mode == COUNTDOWN:
            self._update_countdown(dt)
        elif self.mode == PLAYING:
            self._update_play(dt)
        elif self.mode == PAUSED:
            self.gameover_time += dt
        elif self.mode == DYING:
            self._update_dying(dt)
        elif self.mode == GAMEOVER:
            self.gameover_time += dt
            self._update_particles(dt)
            self._update_popups(dt)
            if self.demo and self.gameover_time >= 2.5:
                self.start_run()

    def _tick_effects(self, dt: float) -> None:
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        if self.shake_timer > 0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
        if self.combo_timer > 0:
            self.combo_timer = max(0.0, self.combo_timer - dt)
            if self.combo_timer == 0:
                self.combo = 0

    def _update_menu(self, dt: float) -> None:
        self.menu_time += dt
        self.scroll = BASE_SCROLL * self.layout.speed_scale * 0.74
        self.scroll_pos += self.scroll * dt
        self.scenery.update(dt, self.scroll)
        self.traffic.update(dt, self.scroll, 0.34, 1.0, spawning=True)
        self._update_particles(dt)
        self._update_popups(dt)

    def _update_countdown(self, dt: float) -> None:
        self.countdown -= dt
        self.player.update(dt)
        self.scroll = BASE_SCROLL * self.layout.speed_scale * 0.45
        self.scroll_pos += self.scroll * dt
        self.scenery.update(dt, self.scroll)
        self.traffic.update(dt, self.scroll, 0.0, 1.0, spawning=False)
        self._update_particles(dt)
        self._update_popups(dt)
        self._emit_exhaust(dt)
        if self.countdown <= 0:
            self.countdown = 0.0
            self.mode = PLAYING
            self.traffic.timer = 0.35
            self.flash(C["accent"], 0.25, 1)
            self.shake(0.18, 0.7)

    def _update_play(self, dt: float) -> None:
        self.run_time += dt
        if self.demo:
            self._demo_drive(dt)
        self.player.update(dt)
        self.difficulty = clamp(self.run_time / SCROLL_RAMP_SECONDS, 0.0, 1.0)
        self.scroll = self._scroll_speed()
        self.scroll_pos += self.scroll * dt
        self.speed_kmh = self.scroll * 13.0
        slow = 0.45 if self.player.slow_timer > 0 else 1.0

        self.scenery.update(dt, self.scroll)
        self.traffic.update(dt, self.scroll, self.difficulty, slow, spawning=True)
        self._update_powerups(dt)
        self._update_particles(dt)
        self._update_popups(dt)
        self._emit_exhaust(dt)

        mult = self.player.score_multiplier
        self.score += (SCORE_SURVIVAL + self.speed_kmh * SCORE_PER_KMH) * mult * dt
        self.distance_m += self.speed_kmh / 3.6 * dt

        self._check_collisions()
        if self.mode != PLAYING:
            return
        self._check_near_misses()

    def _update_dying(self, dt: float) -> None:
        self.dying_timer -= dt
        self.scroll = BASE_SCROLL * self.layout.speed_scale * 0.28
        self.scroll_pos += self.scroll * dt
        self.scenery.update(dt, self.scroll)
        self.traffic.update(dt, self.scroll, self.difficulty, 0.3, spawning=False)
        self._update_particles(dt)
        self._update_popups(dt)
        if self.dying_timer <= 0:
            self._finalise_run()

    def _finalise_run(self) -> None:
        self.final_score = int(self.score)
        self.final_distance = float(self.distance_m)
        self.final_time = float(self.run_time)
        self.new_best = record_run(self.stats, self.final_score, self.final_distance, self.final_time)
        if self.persist:
            save_stats(self.stats, self.stats_path)
        self.mode = GAMEOVER
        self.gameover_time = 0.0
        self.shake(0.45, 1.2)
        if self.new_best:
            self.flash(C["gold"], 0.6, 2)
            for _ in range(24):
                self._spark(self.player.x, self.layout.top + self.player.top / 2, self.rng.choice((C["gold"], C["gold2"], C["white"])), speed=12.0)

    # ------------------------------------------------------------------
    # Power-ups
    # ------------------------------------------------------------------
    def _spawn_powerup(self) -> None:
        if len(self.powerups) >= 2:
            return
        lay = self.layout
        candidates = [
            lane for lane in range(4)
            if not any(car.lane == lane and car.y < 26 * lay.scale for car in self.traffic.cars)
        ]
        if not candidates:
            candidates = list(range(4))
        self.rng.shuffle(candidates)
        lane = candidates[0]
        weights = [
            ("health", 24.0 if self.player.health < PLAYER_MAX_HEALTH else 10.0),
            ("shield", 20.0),
            ("boost", 20.0),
            ("slow", 18.0),
            ("multi", 18.0),
        ]
        total = sum(w for _, w in weights)
        roll = self.rng.uniform(0, total)
        kind = weights[-1][0]
        for name, weight in weights:
            roll -= weight
            if roll <= 0:
                kind = name
                break
        self.powerups.append(
            PowerUp(
                kind=kind,
                lane=lane,
                y=-11 * lay.scale - self.rng.uniform(0, 3 * lay.scale),
                bob_phase=self.rng.random() * math.tau,
            )
        )

    def _update_powerups(self, dt: float) -> None:
        lay = self.layout
        self.powerup_timer -= dt
        if self.powerup_timer <= 0 and self.mode == PLAYING:
            self._spawn_powerup()
            self.powerup_timer = self.rng.uniform(POWERUP_SPAWN_MIN, POWERUP_SPAWN_MAX)

        pbox = self.player.hitbox()
        remaining: list[PowerUp] = []
        for power in self.powerups:
            power.age += dt
            power.y += self.scroll * dt * 0.94
            if power.y > lay.world_half:
                continue
            if power.age > POWERUP_LIFETIME:
                continue
            box = power.hitbox(lay)
            if _overlap(pbox, box):
                self._collect_powerup(power)
                continue
            remaining.append(power)
        self.powerups = remaining

    def _collect_powerup(self, power: PowerUp) -> None:
        label = self.player.apply_powerup(power.kind)
        bonus = 75.0 * self.player.score_multiplier
        if power.kind == "health" and self.player.health >= PLAYER_MAX_HEALTH:
            bonus += 75.0
        self.score += bonus
        self.flash(C["accent2"] if power.kind != "health" else C["green"], 0.34, 1)
        self.shake(0.12, 0.45)
        self._popup(f"{label}  +{int(bonus)}", self.player.x, self._popup_y(), C["gold"], life=1.15)
        colors = (C["accent2"], C["white"], C["gold"])
        for _ in range(14):
            self._spark(
                power.x_for(self.layout),
                power.y + 4 * self.layout.scale,
                self.rng.choice(colors),
                speed=13.0,
            )

    # ------------------------------------------------------------------
    # Collisions, near misses, scoring
    # ------------------------------------------------------------------
    def _check_collisions(self) -> None:
        if self.player.invuln > 0:
            return
        pbox = self.player.hitbox()
        for car in list(self.traffic.cars):
            if car.hit:
                continue
            if _overlap(pbox, car.hitbox(self.layout)):
                self._collide(car)
                if self.mode != PLAYING:
                    return
                return

    def _collide(self, car) -> None:
        lay = self.layout
        if self.player.shield:
            self.player.shield = False
            car.hit = True
            self.traffic.discard(car)
            self.score += 40 * self.player.score_multiplier
            self.flash(C["accent2"], 0.45, 2)
            self.shake(0.42, 1.15)
            self._popup("SHIELD ABSORBED HIT", self.player.x, self._popup_y(), C["accent2"], life=1.2)
            for _ in range(28):
                self._spark(self.player.x, self.player.top + self.player.height / 2, C["accent2"], speed=16.0)
            return

        self.player.health = max(0, self.player.health - 1)
        self.player.invuln = 1.8
        self.player.recover = 0.4
        self.player.nitro = 0.0
        self.player.nitro_timer = 0.0
        self.player.boost_timer = 0.0
        self.player.slow_timer = 0.0
        self.player.multi_timer = 0.0
        self.player.throttle = 0.55
        car.hit = True
        self.traffic.discard(car)
        self.combo = 0
        self.combo_timer = 0.0
        self.flash(C["red_hot"], 0.55, 2)
        self.shake(0.55, 1.4)
        self._popup("-1 HULL", self.player.x, self._popup_y(), C["red"], life=1.1)
        cx = self.player.x
        cy = self.player.top + self.player.height / 2
        for _ in range(34):
            self._spark(cx, cy, self.rng.choice((C["red_hot"], C["orange"], C["gold"], C["white"])), speed=17.0, life=0.7)
        if self.player.health <= 0:
            self._die()

    def _die(self) -> None:
        self.mode = DYING
        self.dying_timer = DYING_TIME
        self.flash(C["red_hot"], 0.8, 3)
        self.shake(0.75, 1.8)
        self._popup("WRECKED", self.player.x, self._popup_y(), C["red_hot"], life=1.4)
        cx = self.player.x
        cy = self.player.top + self.player.height / 2
        for _ in range(64):
            color = self.rng.choice((C["red_hot"], C["orange"], C["gold"], C["yellow"], C["white"], C["burn"]))
            self._spark(cx, cy, color, speed=24.0, life=1.0)

    def _check_near_misses(self) -> None:
        lay = self.layout
        pass_line = self.player.top + self.player.height * 0.5
        for car in list(self.traffic.cars):
            if car.awarded or car.hit:
                continue
            car_h = car.sprite.h * lay.scale
            if car.prev_y + car_h <= pass_line < car.y + car_h:
                car_left = car.left_for(lay)
                car_right = car_left + car.sprite.w * lay.scale
                gap = max(car_left - self.player.right, self.player.left - car_right, 0.0)
                if gap <= NEAR_MISS_THRESHOLD * lay.scale:
                    raw_car = (car_left, car.y, car_right, car.y + car_h)
                    if _overlap(self.player.hitbox(), raw_car):
                        continue
                    car.awarded = True
                    if self.ui_time - self.last_near <= NEAR_MISS_CHAIN_WINDOW:
                        self.combo += 1
                    else:
                        self.combo = 1
                    self.last_near = self.ui_time
                    self.combo_timer = NEAR_MISS_CHAIN_WINDOW
                    points = min(NEAR_MISS_BASE + NEAR_MISS_STEP * (self.combo - 1), NEAR_MISS_MAX)
                    award = points * self.player.score_multiplier
                    self.score += award
                    self.player.nitro = min(NITRO_MAX, self.player.nitro + NEAR_MISS_NITRO)
                    label = f"NEAR MISS +{int(award)}" if self.combo < 2 else f"x{self.combo}  +{int(award)}"
                    self._popup(label, self.player.x, self._popup_y(), C["gold"], life=0.9)
                    self._spark(self.player.x - 5 * lay.scale, self.player.top + self.player.height / 2, C["gold"], speed=8.0)
                    self._spark(self.player.x + 5 * lay.scale, self.player.top + self.player.height / 2, C["gold"], speed=8.0)

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------
    def flash(self, color: int, duration: float = 0.4, strength: int = 1) -> None:
        self.flash_color = color
        self.flash_duration = duration
        self.flash_timer = duration
        self.flash_strength = strength

    def shake(self, duration: float, strength: float) -> None:
        self.shake_duration = max(self.shake_duration, duration)
        self.shake_timer = max(self.shake_timer, duration)
        self.shake_strength = max(self.shake_strength, strength)

    def _popup(self, text: str, x: float, y: float, color: int, life: float = 1.0) -> None:
        self.popups.append(Popup(text=text, x=float(x), y=float(y), color=color, life=life, max_life=life))

    def _spark(self, x: float, y: float, color: int, speed: float = 10.0, life: float = 0.55) -> None:
        ang = self.rng.uniform(0, math.tau)
        mag = self.rng.uniform(0.25, 1.0) * speed
        self.particles.append(
            Particle(
                x=float(x),
                y=float(y),
                vx=math.cos(ang) * mag,
                vy=math.sin(ang) * mag - 2.0,
                life=self.rng.uniform(0.6, 1.0) * life,
                max_life=life,
                color=color,
                size=1 if self.rng.random() < 0.7 else 2,
                drag=1.3,
                gravity=9.0,
                fade=True,
            )
        )

    def _emit_exhaust(self, dt: float) -> None:
        self.exhaust_acc += dt
        rate = 0.045 if self.player.nitro_timer <= 0 else 0.018
        while self.exhaust_acc >= rate:
            self.exhaust_acc -= rate
            lay = self.layout
            x = self.player.x + self.rng.uniform(-1.8, 1.8) * lay.scale
            y = self.player.bottom - 1
            if self.player.nitro_timer > 0:
                color = self.rng.choice((C["accent2"], C["white"], C["orange"]))
                life = 0.32
                vy = -self.rng.uniform(2, 7)
            elif self.player.boost_timer > 0:
                color = self.rng.choice((C["orange"], C["gold"], C["red_hot"]))
                life = 0.4
                vy = -self.rng.uniform(1, 4)
            else:
                color = C["exhaust"] if self.rng.random() < 0.7 else C["burn"]
                life = 0.42
                vy = -self.rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self.rng.uniform(-2.5, 2.5),
                    vy=vy,
                    life=life,
                    max_life=life,
                    color=color,
                    size=1 if self.rng.random() < 0.65 else 2,
                    drag=0.5,
                    gravity=2.0,
                    fade=True,
                )
            )

    def _update_particles(self, dt: float) -> None:
        alive = []
        for particle in self.particles:
            if particle.update(dt):
                alive.append(particle)
        self.particles = alive

    def _update_popups(self, dt: float) -> None:
        alive = []
        for popup in self.popups:
            if popup.update(dt):
                alive.append(popup)
        self.popups = alive

    # ------------------------------------------------------------------
    # Presentation
    # ------------------------------------------------------------------
    def draw(self, canvas) -> None:
        from . import screens

        self.world.reset()
        self.world.draw_scroll_markings(self.scroll_pos)
        self.world.draw_grass_texture(self.scroll_pos)
        self.scenery.draw(self.world)
        self._draw_powerups()
        self.traffic.draw(self.world)
        if self.mode in (COUNTDOWN, PLAYING, PAUSED):
            self._draw_player()
        self._draw_particles()
        self.world.compose(canvas, self.layout.top)

        if self.shake_timer > 0 and self.shake_duration > 0:
            fade = self.shake_timer / self.shake_duration
            amp = self.shake_strength * fade
            dx = int(round(math.sin(self.ui_time * 73.0) * amp))
            dy = int(round(math.cos(self.ui_time * 61.0) * amp * 0.7))
            if dx or dy:
                screens.shake_world(canvas, self.layout.top, self.layout.rows - 2, dx, dy)

        if self.mode != MENU:
            screens.draw_hud(self, canvas)
        screens.draw_popups(self, canvas)
        screens.draw_flash(self, canvas)
        if self.mode == MENU:
            screens.draw_menu(self, canvas)
        elif self.mode == COUNTDOWN:
            screens.draw_countdown(self, canvas)
        elif self.mode == PAUSED:
            screens.draw_pause(self, canvas)
        elif self.mode == GAMEOVER:
            screens.draw_gameover(self, canvas)

        screens.draw_footer(self, canvas)

    def _draw_powerups(self) -> None:
        lay = self.layout
        for power in self.powerups:
            pulse_v = pulse(power.age * 0.9, 1.0)
            bob = math.sin(power.age * 4.2 + power.bob_phase) * 1.2 * lay.scale
            w = power.sprite.w * lay.scale
            left = int(round(power.x_for(lay) - w / 2))
            top = int(round(power.y + bob))
            if top > lay.world_half or top + power.sprite.h * lay.scale < 0:
                continue
            glow = C["gold"] if power.kind == "health" else C["accent2"]
            if pulse_v > 0.55:
                for dx, dy in ((-1, 0), (w, 0), (0, -1), (0, power.sprite.h * lay.scale)):
                    power.sprite.blit(self.world, left + dx, top + dy, lay.scale, tint=glow)
            power.sprite.blit(self.world, left + 1, top + 1, lay.scale, tint=C["shadow"])
            power.sprite.blit(self.world, left, top, lay.scale)

    def _draw_player(self) -> None:
        lay = self.layout
        left = int(round(self.player.left))
        top = int(round(self.player.top))
        top += int(round(math.sin(self.player.bob * 19.0) * 0.5))
        if self.player.shield:
            glow = C["accent2"] if pulse(self.ui_time * 1.6) > 0.45 else C["border"]
            w = self.player.width
            h = self.player.height
            for x in range(left - 1, left + w + 1):
                self.world.put(x, top - 1, glow)
                self.world.put(x, top + h, glow)
            for y in range(top, top + h):
                self.world.put(left - 1, y, glow)
                self.world.put(left + w, y, glow)
        blink = self.player.invuln > 0 and int(self.ui_time * 14) % 2 == 0
        tint = C["white"] if blink else None
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self.player.sprite.blit(self.world, left + ox, top + oy, lay.scale, tint=C["shadow"])
        self.player.sprite.blit(self.world, left + 2, top + 2, lay.scale, tint=C["shadow"])
        self.player.sprite.blit(self.world, left, top, lay.scale, tint=tint)

    def _draw_particles(self) -> None:
        for particle in self.particles:
            x = int(round(particle.x))
            y = int(round(particle.y))
            color = particle.color
            if particle.fade and particle.life < 0.18:
                color = C["dim2"]
            self.world.put(x, y, color)
            if particle.size > 1:
                self.world.put(x + 1, y, color)
                self.world.put(x, y + 1, color)
                self.world.put(x + 1, y + 1, color)


def _overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    """Axis-aligned box overlap, edges touching do not count."""
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]
