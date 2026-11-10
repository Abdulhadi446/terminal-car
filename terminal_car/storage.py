"""Persistent high-score storage (best effort, never crashes the game)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

DEFAULT_STATS = {
    "score": 0,
    "distance_m": 0.0,
    "time": 0.0,
    "runs": 0,
    "last_score": 0,
    "last_distance_m": 0.0,
    "last_time": 0.0,
}


def data_dir() -> Path:
    root = os.environ.get("XDG_DATA_HOME")
    if not root:
        root = os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(root) / "terminal-rush"


def stats_path() -> Path:
    return data_dir() / "highscore.json"


def load_stats(path: Path | None = None) -> dict:
    target = path or stats_path()
    stats = dict(DEFAULT_STATS)
    try:
        with open(target, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            for key, default in DEFAULT_STATS.items():
                value = raw.get(key, default)
                if isinstance(default, float):
                    stats[key] = float(value)
                elif isinstance(default, int):
                    stats[key] = int(value)
            stats["score"] = max(0, stats["score"])
            stats["runs"] = max(0, stats["runs"])
    except (OSError, ValueError, TypeError):
        pass
    return stats


def save_stats(stats: dict, path: Path | None = None) -> bool:
    target = path or stats_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".highscore-", dir=str(target.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(stats, fh, indent=2)
                fh.write("\n")
            os.replace(tmp, target)
        finally:
            try:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            except OSError:
                pass
        return True
    except OSError:
        return False


def record_run(stats: dict, score: int, distance_m: float, time_s: float) -> bool:
    """Record a finished run. Returns True when it is a new personal best."""
    stats["runs"] = int(stats.get("runs", 0)) + 1
    stats["last_score"] = int(score)
    stats["last_distance_m"] = float(distance_m)
    stats["last_time"] = float(time_s)
    best = False
    if score > int(stats.get("score", 0)):
        stats["score"] = int(score)
        best = True
    if distance_m > float(stats.get("distance_m", 0.0)):
        stats["distance_m"] = float(distance_m)
    if time_s > float(stats.get("time", 0.0)):
        stats["time"] = float(time_s)
    return best
