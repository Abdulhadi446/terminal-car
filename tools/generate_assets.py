#!/usr/bin/env python3
"""Asset generator for terminal-car: produces screenshots and demo.gif."""

from __future__ import annotations

import html
import subprocess
import tempfile
from pathlib import Path

from terminal_car.constants import FPS
from terminal_car.game import COUNTDOWN, GAMEOVER, MENU, PLAYING, Game
from terminal_car.layout import make_layout
from terminal_car.terminal import Canvas
from tools.ansi_png import make_svg


def canvas_to_rows(canvas: Canvas) -> list[list[tuple[str, int, int, int]]]:
    rows: list[list[tuple[str, int, int, int]]] = []
    for y in range(canvas.h):
        row = []
        base = y * canvas.w
        for x in range(canvas.w):
            i = base + x
            row.append((canvas.ch[i], canvas.fg[i], canvas.bg[i], canvas.attr[i]))
        rows.append(row)
    return rows


def canvas_to_png(canvas: Canvas, out_path: Path, cell_w: int = 11, cell_h: int = 20, font_size: int = 17) -> None:
    rows = canvas_to_rows(canvas)
    svg = make_svg(rows, cw=cell_w, ch=cell_h, font_size=font_size)
    svg_path = out_path.with_suffix(".svg")
    svg_path.write_text(svg, encoding="utf-8")
    subprocess.run(["magick", str(svg_path), str(out_path)], check=True)
    svg_path.unlink(missing_ok=True)
    print(f"Generated {out_path} ({canvas.w}x{canvas.h})")


def main() -> None:
    assets_dir = Path("assets")
    assets_dir.mkdir(parents=True, exist_ok=True)

    cols = 90
    rows = 28
    layout = make_layout(cols, rows)
    canvas = Canvas(cols, rows)

    # 1. Title Screen
    print("Capturing title screen...")
    game = Game(layout, stats={"score": 3480, "distance_m": 4250.0, "time": 95.0}, seed=42, persist=False)
    game.draw(canvas)
    canvas_to_png(canvas, assets_dir / "title.png")

    # 2. Gameplay & Demo GIF recording
    print("Simulating gameplay & recording demo frames...")
    game = Game(layout, stats={"score": 3480, "distance_m": 4250.0, "time": 95.0}, seed=105, persist=False, demo=True)
    game.start_run()
    game.countdown = 0.0
    game.mode = PLAYING

    dt = 1.0 / FPS
    frames_dir = Path(tempfile.mkdtemp(prefix="rush_frames_"))

    recorded_frames = 0
    max_frames = 120  # ~4 seconds of continuous action at 30 fps

    # Warm up a bit so traffic is on screen
    for _ in range(60):
        game.update(dt)

    captured_gameplay = False
    captured_nitro = False

    for frame_idx in range(max_frames):
        game.update(dt)
        game.draw(canvas)

        # Capture single screenshots at good moments
        if frame_idx == 20 and not captured_gameplay:
            canvas_to_png(canvas, assets_dir / "gameplay.png")
            captured_gameplay = True

        if game.player.nitro_timer > 0 and not captured_nitro:
            canvas_to_png(canvas, assets_dir / "nitro.png")
            captured_nitro = True

        # Render frame for GIF
        frame_svg = frames_dir / f"frame_{frame_idx:04d}.svg"
        frame_png = frames_dir / f"frame_{frame_idx:04d}.png"
        rows_data = canvas_to_rows(canvas)
        svg_content = make_svg(rows_data, cw=10, ch=18, font_size=15)
        frame_svg.write_text(svg_content, encoding="utf-8")
        subprocess.run(["magick", str(frame_svg), str(frame_png)], check=True)
        frame_svg.unlink()
        recorded_frames += 1

    if not captured_nitro:
        # If nitro wasn't active during the slice, trigger it and snap
        game.player.nitro = 50.0
        game.player.try_nitro()
        game.update(dt)
        game.draw(canvas)
        canvas_to_png(canvas, assets_dir / "nitro.png")

    # 3. Game Over Screen
    print("Generating game over screen...")
    game.mode = GAMEOVER
    game.score = 2840.0
    game.distance_m = 3280.0
    game.near_misses = 14
    game.top_speed_kmh = 184.2
    game.final_time = 62.5
    game.draw(canvas)
    canvas_to_png(canvas, assets_dir / "game-over.png")

    # 4. Compile GIF using ffmpeg
    print(f"Compiling demo.gif from {recorded_frames} frames...")
    gif_path = assets_dir / "demo.gif"
    palette_png = frames_dir / "palette.png"

    # High quality palettegen ffmpeg pipeline
    subprocess.run([
        "ffmpeg", "-y", "-framerate", "25",
        "-i", str(frames_dir / "frame_%04d.png"),
        "-vf", "fps=25,scale=800:-1:flags=lanczos,palettegen=stats_mode=diff",
        str(palette_png)
    ], check=True)

    subprocess.run([
        "ffmpeg", "-y", "-framerate", "25",
        "-i", str(frames_dir / "frame_%04d.png"),
        "-i", str(palette_png),
        "-lavfi", "fps=25,scale=800:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3",
        str(gif_path)
    ], check=True)

    # Cleanup temp frames
    for f in frames_dir.glob("*"):
        f.unlink(missing_ok=True)
    frames_dir.rmdir()

    print(f"Successfully generated all assets including {gif_path}!")


if __name__ == "__main__":
    main()
