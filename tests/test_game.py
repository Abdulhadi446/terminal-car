"""Basic smoke tests for Terminal Rush (terminal-car)."""

import unittest
from terminal_car.constants import LANES, MIN_COLS, MIN_ROWS
from terminal_car.layout import make_layout
from terminal_car.game import Game, MENU, PLAYING
from terminal_car.terminal import Canvas
from terminal_car.sprites import car_sprite


class TestTerminalCar(unittest.TestCase):
    def test_layout_creation(self):
        layout = make_layout(80, 24)
        self.assertIsNotNone(layout)
        self.assertGreaterEqual(layout.cols, MIN_COLS)
        self.assertGreaterEqual(layout.rows, MIN_ROWS)
        centers = [layout.lane_center(i) for i in range(LANES)]
        self.assertEqual(len(centers), LANES)

    def test_game_lifecycle(self):
        layout = make_layout(80, 24)
        game = Game(layout, persist=False)
        self.assertEqual(game.mode, MENU)

        game.start_run()
        game.countdown = 0.0
        game.mode = PLAYING
        self.assertEqual(game.mode, PLAYING)

        # Step physics
        game.update(0.033)
        self.assertGreater(game.speed_kmh, 0.0)

    def test_canvas_draw(self):
        layout = make_layout(80, 24)
        canvas = Canvas(80, 24)
        game = Game(layout, persist=False)
        game.draw(canvas)
        # Should not raise
        self.assertEqual(canvas.w, 80)
        self.assertEqual(canvas.h, 24)

    def test_sprites(self):
        sprite = car_sprite("sedan", "red", facing_down=False)
        self.assertGreater(sprite.w, 0)
        self.assertGreater(sprite.h, 0)


if __name__ == "__main__":
    unittest.main()
