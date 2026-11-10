"""All screen chrome: HUD, menu, countdown, pause, game over and effects."""

from __future__ import annotations

import curses

from .constants import (
    C,
    COUNTDOWN_TIME,
    PLAYER_MAX_HEALTH,
    POWERUP_STYLE,
    TITLE,
    TAGLINE,
)
from .terminal import GLYPHS
from .utils import fmt_dist, fmt_score, fmt_time, pulse

BOLD = getattr(curses, "A_BOLD", 0)


# ---------------------------------------------------------------------------
# Small drawing helpers
# ---------------------------------------------------------------------------
def _hints_width(hints, gap: int = 2) -> int:
    if not hints:
        return 0
    return sum(len(key) + 2 + (1 + len(label) if label else 0) for key, label in hints) + gap * (len(hints) - 1)


def draw_key_hints(canvas, x, y, hints, gap: int = 2, bg: int | None = None,
                   key_color: int = C["accent"], label_color: int = C["dim"]) -> int:
    """Draw [KEY] LABEL hints; returns the x just past the last hint."""
    for index, (key, label) in enumerate(hints):
        if index:
            x += gap
        if bg is not None:
            canvas.fill(x, y, len(key) + 2, 1, " ", key_color, bg)
        canvas.text(x, y, "[", C["border"], bg)
        canvas.text(x + 1, y, key, key_color, bg, BOLD)
        canvas.text(x + 1 + len(key), y, "]", C["border"], bg)
        x += len(key) + 2
        if label:
            canvas.text(x + 1, y, label, label_color, bg)
            x += 1 + len(label)
    return x


def center_hints(canvas, y, hints, gap: int = 2, bg: int | None = None,
                 key_color: int = C["accent"], label_color: int = C["dim"]) -> None:
    width = _hints_width(hints, gap)
    x = max(1, (canvas.w - width) // 2)
    draw_key_hints(canvas, x, y, hints, gap, bg, key_color, label_color)


def _fit_hints(hints, width: int, gap: int = 2):
    if _hints_width(hints, gap) <= width:
        return hints
    for count in range(len(hints) - 1, 0, -1):
        candidate = hints[:count]
        if _hints_width(candidate, gap) <= width:
            return candidate
    return hints[:1]


def _panel(canvas, width: int, height: int, border: int = C["border"],
           bg: int = C["panel"], style: str = "double") -> tuple[int, int]:
    width = max(20, min(width, canvas.w - 2))
    height = max(6, min(height, canvas.h - 2))
    x = (canvas.w - width) // 2
    y = max(0, (canvas.h - height) // 2)
    canvas.box(x, y, width, height, border, bg, style=style, shadow=C["shadow"])
    return x, y


def _top_chrome(canvas, left: str, right: str) -> None:
    canvas.fill(0, 0, canvas.w, 3, " ", C["offwhite"], C["ink"])
    canvas.text(1, 0, left, C["accent"], C["ink"], BOLD)
    right_text = right[: max(0, canvas.w - 2)]
    canvas.text(max(1, canvas.w - len(right_text) - 1), 0, right_text, C["dim"], C["ink"])
    canvas.hline(0, 2, canvas.w, C["border_dim"], C["ink"], "─" if GLYPHS.fancy else "-")


def _draw_effect_strip(canvas, x_right: int, y: int, game, bg: int) -> int:
    entries: list[tuple[str, int]] = []
    if game.player.shield:
        entries.append(("SHIELD", C["accent2"]))
    if game.player.boost_timer > 0:
        entries.append((f"BOOST {game.player.boost_timer:0.1f}", C["orange"]))
    if game.player.slow_timer > 0:
        entries.append((f"SLOW {game.player.slow_timer:0.1f}", C["accent"]))
    if game.player.multi_timer > 0:
        entries.append((f"x2 {game.player.multi_timer:0.1f}", C["magenta"]))
    if game.player.nitro_timer > 0:
        entries.append((f"NITRO {game.player.nitro_timer:0.1f}", C["accent2"]))
    if not entries:
        if game.player.nitro >= 40:
            entries.append(("NITRO READY", C["accent"]))
        else:
            entries.append(("CHARGE NITRO", C["dim2"]))
    x = x_right
    for index in range(len(entries) - 1, -1, -1):
        label, color = entries[index]
        x -= len(label)
        canvas.text(x, y, label, color, bg)
        x -= 2
    return x


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
def draw_hud(game, canvas) -> None:
    w = canvas.w
    canvas.fill(0, 0, w, 3, " ", C["offwhite"], C["ink"])

    # row 0: identity, score, best
    logo = f"{GLYPHS.bullet} TERMINAL RUSH"
    if w < 72:
        logo = f"{GLYPHS.bullet} TERMINAL"
    if w < 58:
        logo = f"{GLYPHS.bullet} TR"
    canvas.text(1, 0, logo, C["accent"], C["ink"], BOLD)
    score_txt = f"SCORE {fmt_score(int(game.score))}"
    best_txt = f"BEST {fmt_score(game.best_score)}"
    if w >= 74:
        canvas.text((w - len(score_txt)) // 2, 0, score_txt, C["gold"], C["ink"], BOLD)
        canvas.text(max(1, w - len(best_txt) - 1), 0, best_txt, C["green"], C["ink"])
    else:
        combined = f"{score_txt}  {best_txt}"
        x = max(1, w - len(combined) - 1)
        canvas.text(x, 0, score_txt, C["gold"], C["ink"], BOLD)
        canvas.text(x + len(score_txt) + 2, 0, best_txt, C["green"], C["ink"])

    # row 1: hull / speed / distance / nitro
    y = 1
    wide = w >= 68
    x = 1
    canvas.text(x, y, "HULL" if wide else "HP", C["dim"], C["ink"])
    x += 5 if wide else 3
    for i in range(PLAYER_MAX_HEALTH):
        alive = i < game.player.health
        color = C["green"] if alive else C["dim3"]
        if alive and game.player.health == 1:
            color = C["red"] if pulse(game.ui_time * 3.0) > 0.4 else C["red_dark"]
        canvas.text(x + i, y, GLYPHS.full, color, C["ink"])
    x += PLAYER_MAX_HEALTH + 2

    canvas.text(x, y, "SPD", C["dim"], C["ink"])
    speed = f"{int(game.speed_kmh):3d}"
    canvas.text(x + 4, y, speed, C["offwhite"], C["ink"], BOLD)
    x += 7
    if wide:
        canvas.text(x, y, "KM/H", C["dim2"], C["ink"])
        x += 6
    x += 1

    if w >= 60:
        canvas.text(x, y, "DIST", C["dim"], C["ink"])
        canvas.text(x + 5, y, fmt_dist(game.distance_m), C["offwhite"], C["ink"])
        x += 16 if wide else 14
        x += 1

    nitro_len = 9 if wide else 6
    canvas.text(x, y, "NOS", C["dim"], C["ink"])
    x += 4
    filled = int(round(nitro_len * min(1.0, game.player.nitro / 100.0)))
    ready = game.player.nitro >= 40
    for i in range(nitro_len):
        if i < filled:
            color = C["accent2"] if ready else C["blue"]
        else:
            color = C["dim3"]
        canvas.text(x + i, y, GLYPHS.full if i < filled else GLYPHS.shade, color, C["ink"])

    # row 2: status, combo, active effects
    canvas.fill(0, 2, w, 1, " ", C["offwhite"], C["ink2"])
    effects_right = w - 1
    x_effects = _draw_effect_strip(canvas, effects_right, 2, game, C["ink2"])
    status, status_color = _status(game)
    available = max(4, x_effects - 2)
    if len(status) > available:
        status = status[: max(0, available - 3)] + "..."
    canvas.text(1, 2, status, status_color, C["ink2"])
    if game.combo > 1 and game.combo_timer > 0:
        combo = f"CHAIN x{game.combo}"
        cx = 1 + len(status) + 2
        if cx + len(combo) < x_effects:
            canvas.text(cx, 2, combo, C["gold"], C["ink2"], BOLD)


def _status(game) -> tuple[str, int]:
    p = game.player
    if game.mode == "countdown":
        return "LIGHTS OUT IN A MOMENT", C["gold"]
    if game.mode == "dying":
        return "SIGNAL LOST", C["red"]
    if p.oncoming:
        return "WRONG WAY — ONCOMING TRAFFIC", C["red"]
    if p.invuln > 0:
        return "HULL DAMAGED", C["red"]
    if game.combo > 1 and game.combo_timer > 0:
        return f"NEAR-MISS CHAIN x{game.combo}", C["gold"]
    if p.slow_timer > 0:
        return "TIME DILATION ACTIVE", C["accent"]
    if p.boost_timer > 0:
        return "BOOST ENGAGED", C["orange"]
    if game.difficulty > 0.72:
        return "TRAFFIC CRITICAL · HOLD THE LINE", C["red"]
    if game.difficulty > 0.35:
        return "TRAFFIC HEAVY · FIND A GAP", C["gold2"]
    if p.shield:
        return "SHIELD READY", C["accent2"]
    return f"HIGHWAY OPEN · LANE {p.lane + 1}", C["dim"]


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
def draw_footer(game, canvas) -> None:
    y = canvas.h - 1
    canvas.fill(0, y, canvas.w, 1, " ", C["dim"], C["ink"])
    mode = game.mode
    if mode in ("menu", "paused", "gameover"):
        canvas.center(y, "TERMINAL RUSH  //  ARCADE HIGHWAY", C["dim2"], C["ink"])
        return
    if mode == "countdown":
        hints = [("SPACE", "SKIP"), ("Q", "QUIT")]
    elif mode == "dying":
        hints = [("Q", "QUIT")]
    else:
        steer = f"{GLYPHS.arrow_l}/{GLYPHS.arrow_r}"
        throttle = f"{GLYPHS.arrow_u}/{GLYPHS.arrow_d}"
        if canvas.w >= 66:
            hints = [
                (steer, "STEER"), (throttle, "THROTTLE"), ("SPACE", "NITRO"),
                ("P", "PAUSE"), ("Q", "QUIT"),
            ]
        else:
            hints = [
                (f"{GLYPHS.arrow_l}{GLYPHS.arrow_r}", "STEER"),
                ("SPACE", "NITRO"), ("P", "PAUSE"), ("Q", "QUIT"),
            ]
    hints = _fit_hints(hints, canvas.w - 4)
    center_hints(canvas, y, hints, 2, C["ink"], C["accent"], C["dim"])


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------
def draw_menu(game, canvas) -> None:
    _top_chrome(canvas, f"{GLYPHS.bullet} ARCADE HIGHWAY", TITLE)
    w, h = canvas.w, canvas.h
    pw = min(80, w - 2)
    ph = min(23, h - 4)
    rich = pw >= 68 and ph >= 23
    x, y = _panel(canvas, pw, ph, C["border"], C["panel"], "double")
    bg = C["panel"]
    steer = f"{GLYPHS.arrow_l}/{GLYPHS.arrow_r}"
    throttle = f"{GLYPHS.arrow_u}/{GLYPHS.arrow_d}"

    if rich:
        py = y + 2
        colors = [C["gold"], C["white"], C["gold2"], C["white"], C["accent2"]]
        canvas.pixel_text_center(py, TITLE, colors, 1, 1, 1, C["shadow"], bg)
        canvas.center(py + 6, TAGLINE, C["dim"], bg)
        canvas.hline(x + 9, py + 7, pw - 18, C["border_dim"], bg, "─" if GLYPHS.fancy else "-")
        canvas.center(py + 9, "DODGE TRAFFIC. GRAB POWER-UPS. SURVIVE.", C["offwhite"], bg, BOLD)
        center_hints(canvas, py + 11, [(steer, "STEER"), (throttle, "THROTTLE")], 3, bg,
                     C["accent"], C["dim"])
        center_hints(canvas, py + 12, [("SPACE", "NITRO BOOST")], 3, bg,
                     C["accent"], C["dim"])
        center_hints(canvas, py + 13, [("P", "PAUSE"), ("R", "RESTART"), ("Q", "QUIT")], 3, bg,
                     C["accent"], C["dim"])
        legends = [
            ("HEALTH", C["red"]), ("SHIELD", C["accent2"]), ("BOOST", C["gold"]),
            ("SLOW-MO", C["blue"]), ("x2 SCORE", C["magenta"]),
        ]
        legend_width = sum(len(name) for name, _ in legends) + 3 * (len(legends) - 1)
        lx = max(x + 2, x + (pw - legend_width) // 2)
        for index, (name, color) in enumerate(legends):
            canvas.text(lx, py + 15, name, color, bg)
            lx += len(name)
            if index < len(legends) - 1:
                canvas.text(lx + 1, py + 15, GLYPHS.dot, C["dim3"], bg)
                lx += 3
        best = f"PERSONAL BEST  {fmt_score(game.best_score)}"
        canvas.center(py + 17, best, C["gold"], bg, BOLD)
        prompt = "PRESS ENTER TO DRIVE"
        blink = pulse(game.menu_time * 0.9) > 0.28
        canvas.center(y + ph - 2, f"[ {prompt} ]", C["accent"] if blink else C["border_dim"], bg, BOLD)
    else:
        py = y + 2
        canvas.center(py, "T E R M I N A L   R U S H", C["gold"], bg, BOLD)
        canvas.center(py + 1, TAGLINE, C["dim2"], bg)
        canvas.center(py + 3, "DODGE TRAFFIC · SURVIVE", C["offwhite"], bg)
        center_hints(canvas, py + 5, [(steer, "STEER"), ("SPACE", "NITRO")], 2, bg,
                     C["accent"], C["dim"])
        center_hints(canvas, py + 6, [("P", "PAUSE"), ("Q", "QUIT")], 2, bg,
                     C["accent"], C["dim"])
        canvas.center(py + 8, f"BEST  {fmt_score(game.best_score)}", C["gold"], bg, BOLD)
        blink = pulse(game.menu_time * 0.9) > 0.28
        canvas.center(y + ph - 2, "[ ENTER ] DRIVE", C["accent"] if blink else C["border_dim"], bg, BOLD)


# ---------------------------------------------------------------------------
# Countdown
# ---------------------------------------------------------------------------
def draw_countdown(game, canvas) -> None:
    lay = game.layout
    area_top = lay.top
    area_bottom = lay.rows - 2
    ph = min(16, max(11, area_bottom - area_top + 1))
    pw = min(42, canvas.w - 6)
    x = (canvas.w - pw) // 2
    y = area_top + max(0, (area_bottom - area_top + 1 - ph) // 2)
    canvas.box(x, y, pw, ph, C["accent"], C["ink2"], style="double", shadow=C["shadow"])
    canvas.center(y + 1, "GET READY", C["gold"], C["ink2"], BOLD)
    if game.countdown > 2.2:
        label = "3"
    elif game.countdown > 1.2:
        label = "2"
    elif game.countdown > 0.2:
        label = "1"
    else:
        label = "GO!"
    colors = [C["gold"], C["white"], C["gold2"]]
    if ph >= 15:
        canvas.pixel_text_center(y + 3, label, colors, 2, 2, 2, C["shadow"], C["ink2"])
        canvas.center(y + ph - 2, "DODGE THE TRAFFIC", C["dim"], C["ink2"])
    else:
        canvas.pixel_text_center(y + 3, label, colors, 1, 1, 1, C["shadow"], C["ink2"])
        canvas.center(y + ph - 2, "DODGE THE TRAFFIC", C["dim"], C["ink2"])


# ---------------------------------------------------------------------------
# Pause
# ---------------------------------------------------------------------------
def draw_pause(game, canvas) -> None:
    canvas.dim()
    pw = min(48, canvas.w - 6)
    ph = min(15, canvas.h - 4)
    x, y = _panel(canvas, pw, ph, C["gold"], C["panel"], "double")
    bg = C["panel"]
    canvas.pixel_text_center(y + 2, "PAUSED", [C["gold"], C["white"]], 1, 1, 1, C["shadow"], bg)
    stat = f"SCORE {fmt_score(int(game.score))}   ·   {fmt_dist(game.distance_m)}"
    if len(stat) <= pw - 4:
        canvas.center(y + 8, stat, C["offwhite"], bg)
    else:
        canvas.center(y + 8, f"SCORE {fmt_score(int(game.score))}", C["offwhite"], bg)
    center_hints(canvas, y + 10, [("P", "RESUME"), ("R", "RESTART")], 2, bg,
                 C["accent"], C["dim"])
    center_hints(canvas, y + 11, [("ENTER", "MENU"), ("Q", "QUIT")], 2, bg,
                 C["accent"], C["dim"])
    if ph >= 13:
        canvas.center(y + ph - 2, "ENGINE IDLING", C["dim2"], bg)


# ---------------------------------------------------------------------------
# Game over
# ---------------------------------------------------------------------------
def draw_gameover(game, canvas) -> None:
    canvas.dim()
    pw = min(60, canvas.w - 6)
    ph = min(20, canvas.h - 2)
    rich = pw >= 52 and ph >= 17
    x, y = _panel(canvas, pw, ph, C["red"], C["panel"], "double")
    bg = C["panel"]
    if rich:
        canvas.pixel_text_center(y + 2, "WRECKED", [C["red_hot"], C["red"], C["orange"]],
                                 2, 2, 2, C["shadow"], bg)
        canvas.center(y + 12, "RUN TERMINATED · SIGNAL LOST", C["dim"], bg)
        col1 = x + 6
        col2 = x + pw // 2 + 2
        row = y + 14
        _stat_line(canvas, col1, row, "SCORE", fmt_score(game.final_score), C["gold"], bg)
        _stat_line(canvas, col1, row + 1, "DISTANCE", fmt_dist(game.final_distance), C["offwhite"], bg)
        _stat_line(canvas, col2, row, "TIME", fmt_time(game.final_time), C["offwhite"], bg)
        _stat_line(canvas, col2, row + 1, "PERSONAL BEST", fmt_score(game.best_score), C["green"], bg)
        if game.new_best:
            canvas.center(y + 16, f"{GLYPHS.bullet} NEW PERSONAL BEST {GLYPHS.bullet}", C["gold"], bg, BOLD)
        hints = _fit_hints([("R", "RETRY"), ("ENTER", "MENU"), ("Q", "QUIT")], pw - 6)
        center_hints(canvas, y + ph - 2, hints, 2, bg, C["accent"], C["dim"])
    else:
        canvas.center(y + 2, "W R E C K E D", C["red_hot"], bg, BOLD)
        _stat_line(canvas, x + 4, y + 4, "SCORE", fmt_score(game.final_score), C["gold"], bg)
        _stat_line(canvas, x + 4, y + 5, "DIST", fmt_dist(game.final_distance), C["offwhite"], bg)
        _stat_line(canvas, x + 4, y + 6, "TIME", fmt_time(game.final_time), C["offwhite"], bg)
        _stat_line(canvas, x + 4, y + 7, "BEST", fmt_score(game.best_score), C["green"], bg)
        if game.new_best:
            canvas.center(y + 9, f"{GLYPHS.bullet} NEW BEST {GLYPHS.bullet}", C["gold"], bg, BOLD)
        hints = _fit_hints([("R", "RETRY"), ("ENTER", "MENU"), ("Q", "QUIT")], pw - 4)
        center_hints(canvas, y + ph - 2, hints, 2, bg, C["accent"], C["dim"])


def _stat_line(canvas, x, y, label: str, value: str, value_color: int, bg: int) -> None:
    canvas.text(x, y, label, C["dim"], bg)
    canvas.text(x + 15, y, value, value_color, bg, BOLD)


# ---------------------------------------------------------------------------
# Effects and overlays
# ---------------------------------------------------------------------------
def draw_popups(game, canvas) -> None:
    for popup in game.popups[-5:]:
        if popup.life <= 0:
            continue
        text = popup.text
        if len(text) > canvas.w - 2:
            text = text[: canvas.w - 3] + "..."
        x = int(round(popup.x - len(text) / 2))
        x = max(1, min(canvas.w - len(text) - 1, x))
        y = int(round(popup.y))
        color = popup.color if popup.life > 0.22 else C["dim2"]
        canvas.fill(x - 1, y, len(text) + 2, 1, " ", color, popup.bg)
        canvas.text(x, y, text, color, popup.bg, BOLD)


def draw_flash(game, canvas) -> None:
    if game.flash_timer <= 0 or game.flash_duration <= 0:
        return
    strength = game.flash_strength
    if not strength:
        return
    color = game.flash_color
    top, bottom = game.layout.top, canvas.h - 2
    if bottom <= top:
        return
    intensity = game.flash_timer / game.flash_duration
    # while fading, break the frame into dashes so it feels like a glow
    step = 1 if intensity > 0.45 or strength >= 3 else 2
    for x in range(0, canvas.w, step):
        canvas.set(x, top, " ", color, color)
        canvas.set(x, bottom, " ", color, color)
        if strength >= 2:
            canvas.set(x, top + 1, " ", color, color)
            canvas.set(x, bottom - 1, " ", color, color)
    for y in range(top, bottom + 1, step):
        canvas.set(0, y, " ", color, color)
        canvas.set(canvas.w - 1, y, " ", color, color)
        if strength >= 2:
            canvas.set(1, y, " ", color, color)
            canvas.set(canvas.w - 2, y, " ", color, color)
    if strength >= 3:
        for x in range(0, min(8, canvas.w)):
            for y in range(top, min(top + 5, bottom)):
                canvas.set(x, y, " ", color, color)
                canvas.set(canvas.w - 1 - x, y, " ", color, color)


def shake_world(canvas, top: int, bottom: int, dx: int, dy: int) -> None:
    """Shift the composed world region by whole terminal cells."""
    if (not dx and not dy) or bottom <= top:
        return
    top = max(0, top)
    bottom = min(canvas.h - 1, bottom)
    rows: list[list[tuple[str, int, int, int]]] = []
    for y in range(top, bottom + 1):
        src_y = min(bottom, max(top, y - dy))
        base = src_y * canvas.w
        row = []
        for x in range(canvas.w):
            src_x = min(canvas.w - 1, max(0, x - dx))
            i = base + src_x
            row.append((canvas.ch[i], canvas.fg[i], canvas.bg[i], canvas.attr[i]))
        rows.append(row)
    for offset, row in enumerate(rows):
        y = top + offset
        base = y * canvas.w
        for x, (ch, fg, bg, attr) in enumerate(row):
            i = base + x
            canvas.ch[i] = ch
            canvas.fg[i] = fg
            canvas.bg[i] = bg
            canvas.attr[i] = attr


# ---------------------------------------------------------------------------
# Tiny terminal fallback
# ---------------------------------------------------------------------------
def draw_too_small(canvas, cols: int, rows: int) -> None:
    canvas.fill(0, 0, canvas.w, canvas.h, " ", C["offwhite"], C["ink"])
    title = "TERMINAL TOO SMALL"
    need = "NEED AT LEAST 54 x 18"
    current = f"CURRENT {cols} x {rows}"
    lines = [title, "", need, current, "", "RESIZE TO CONTINUE", "[Q] QUIT"]
    top = max(0, (canvas.h - len(lines)) // 2)
    for index, line in enumerate(lines):
        if not line:
            continue
        if index == 0:
            canvas.center(top + index, line, C["red_hot"], C["ink"], BOLD)
        elif index in (2, 3):
            canvas.center(top + index, line, C["offwhite"], C["ink"])
        elif index == 5:
            canvas.center(top + index, line, C["accent"], C["ink"])
        else:
            canvas.center(top + index, line, C["dim"], C["ink"])
    if canvas.w > len(title) + 2 and canvas.h > len(lines) + 2:
        canvas.box(1, max(0, top - 2), canvas.w - 2, min(canvas.h - 2, len(lines) + 4),
                   C["border_dim"], C["ink"], "single")
