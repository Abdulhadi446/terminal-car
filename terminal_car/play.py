"""Curses entry point for Terminal Rush.

The loop is deliberately small: it owns the terminal, normalises input,
handles resizes and drives the ``Game`` object at a fixed frame rate.
All game rules live in :mod:`terminal_car.game`.
"""

from __future__ import annotations

import argparse
import curses
import locale
import sys
import time
import traceback
from pathlib import Path

from . import screens
from .constants import APP_NAME, FPS, MAX_DT, VERSION
from .game import EXIT, Game
from .layout import make_layout
from .storage import load_stats, stats_path
from .terminal import Canvas, Colors, Renderer

CRASH_LOG = Path("/tmp/terminal-rush-crash.log")

_SPECIAL_KEYS = {
    curses.KEY_LEFT: "left",
    curses.KEY_RIGHT: "right",
    curses.KEY_UP: "up",
    curses.KEY_DOWN: "down",
    curses.KEY_ENTER: "enter",
    curses.KEY_BACKSPACE: "backspace",
    curses.KEY_DC: "backspace",
}

_CHAR_KEYS = {
    3: "quit",          # Ctrl-C
    8: "backspace",
    9: "space",         # Tab is a forgiving start / skip key
    10: "enter",
    13: "enter",
    27: "escape",
    32: "space",
    127: "backspace",
}


def normalise_key(key: int) -> str | None:
    """Translate a curses key code into a stable, lower-case action name."""
    if key == curses.KEY_RESIZE:
        return None
    special = _SPECIAL_KEYS.get(key)
    if special:
        return special
    char = _CHAR_KEYS.get(key)
    if char:
        return char
    if 0 <= key < 256:
        try:
            text = chr(key).lower()
        except ValueError:
            return None
        if text.isprintable() and text:
            return text
    return None


class App:
    """Owns terminal resources and the current game instance."""

    def __init__(self, screen, seed: int | None = None, demo: bool = False):
        self.screen = screen
        self.seed = seed
        self.demo = demo
        self.stats = load_stats()
        self.game: Game | None = None
        self.layout = None
        self.canvas: Canvas | None = None
        self.renderer: Renderer | None = None
        self.running = True
        self.last_time = time.monotonic()

        self._setup_terminal()
        # COLOR values are only published by ncurses *after* start_color().
        # Calling it here also makes the pair count available to the renderer.
        try:
            curses.start_color()
            curses.use_default_colors()
        except curses.error:
            pass
        colors = Colors(
            getattr(curses, "COLORS", 0),
            getattr(curses, "COLOR_PAIRS", 0),
            enabled=getattr(curses, "has_colors", lambda: False)(),
        )
        height, width = screen.getmaxyx()
        self.canvas = Canvas(width, height)
        self.renderer = Renderer(screen, colors)
        self._resize(width, height, initial=True)

    # ------------------------------------------------------------------
    # Terminal lifecycle
    # ------------------------------------------------------------------
    def _setup_terminal(self) -> None:
        try:
            curses.set_escdelay(25)
        except (AttributeError, curses.error):
            pass
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        try:
            self.screen.keypad(True)
            self.screen.nodelay(True)
            curses.noecho()
            curses.cbreak()
        except curses.error:
            pass
        try:
            self.screen.timeout(0)
        except curses.error:
            pass

    def _resize(self, width: int, height: int, initial: bool = False) -> None:
        if self.canvas is None:
            self.canvas = Canvas(width, height)
        else:
            self.canvas.resize(width, height)
        if self.renderer is not None:
            self.renderer.invalidate()
        layout = make_layout(width, height)
        self.layout = layout
        if layout is None:
            # Keep an active game alive while the user enlarges the window.
            return
        if self.game is None:
            self.game = Game(
                layout,
                stats=self.stats,
                stats_path=stats_path(),
                seed=self.seed,
                demo=self.demo,
            )
            if self.demo:
                self.game.start_run()
        else:
            self.game.relayout(layout)

    # ------------------------------------------------------------------
    # Input / frame loop
    # ------------------------------------------------------------------
    def _read_keys(self) -> bool:
        """Drain pending keys. Returns False if the app should close."""
        for _ in range(64):
            try:
                key = self.screen.getch()
            except curses.error:
                break
            if key == -1:
                break
            if key == curses.KEY_RESIZE:
                height, width = self.screen.getmaxyx()
                self._resize(width, height)
                continue
            name = normalise_key(key)
            if name is None:
                continue
            if self.game is None:
                if name in ("q", "quit", "escape"):
                    return False
                continue
            if not self.game.handle_key(name):
                return False
        return True

    def frame(self, dt: float) -> None:
        assert self.canvas is not None and self.renderer is not None
        height, width = self.screen.getmaxyx()
        if width != self.canvas.w or height != self.canvas.h:
            self._resize(width, height)

        if not self._read_keys():
            self.running = False
            return

        if self.layout is None or self.game is None:
            screens.draw_too_small(self.canvas, self.canvas.w, self.canvas.h)
        else:
            self.game.update(dt)
            self.game.draw(self.canvas)

        self.renderer.present(self.canvas)
        if self.game is not None and self.game.mode == EXIT:
            self.running = False

    def run(self) -> None:
        target = 1.0 / FPS
        try:
            while self.running:
                now = time.monotonic()
                dt = now - self.last_time
                self.last_time = now
                if dt < 0:
                    dt = 0.0
                # A long terminal stall should not teleport traffic into the player.
                dt = min(dt, MAX_DT)
                self.frame(dt)
                elapsed = time.monotonic() - now
                if elapsed < target:
                    time.sleep(target - elapsed)
        finally:
            if self.game is not None:
                self.game.save_on_exit()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="Endless top-down highway survival, played entirely in your terminal.",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="fixed RNG seed (useful for practising a layout)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="skip the menu and start a run immediately",
    )
    return parser.parse_args(argv)


def _report_crash(exc: BaseException) -> None:
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        CRASH_LOG.write_text(text, encoding="utf-8")
        location = str(CRASH_LOG)
    except OSError:
        location = "the crash log"
    print(f"\n{APP_NAME} hit an unexpected error. Details were written to {location}.", file=sys.stderr)
    print("Your terminal has been restored. Run the game again to retry.", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    locale.setlocale(locale.LC_ALL, "")
    args = _parse_args(argv)
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("terminal-rush must be run inside an interactive terminal.", file=sys.stderr)
        return 2
    try:
        def wrapped(screen):
            App(screen, seed=args.seed, demo=args.demo).run()

        curses.wrapper(wrapped)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # noqa: BLE001 - top level safety net
        _report_crash(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
