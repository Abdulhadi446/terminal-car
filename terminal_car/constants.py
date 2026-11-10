"""Tunable constants, palette and pixel fonts for Terminal Rush."""

APP_NAME = "terminal-rush"
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Gameplay tuning (all distances are in *base* half-block pixels at 1x scale)
# ---------------------------------------------------------------------------
LANES = 4
ONCOMING_LANES = (0, 1)
FORWARD_LANES = (2, 3)

PLAYER_START_LANE = 2
PLAYER_MAX_HEALTH = 3
START_HEALTH = 3

MIN_COLS = 54
MIN_ROWS = 18

FPS = 30.0
MAX_DT = 0.05

BASE_SCROLL = 8.2          # half rows / second at difficulty 0
MAX_SCROLL = 13.6          # half rows / second at max difficulty
SCROLL_RAMP_SECONDS = 165.0

COUNTDOWN_TIME = 3.2
DYING_TIME = 1.25

NITRO_MAX = 100.0
NITRO_START = 45.0
NITRO_COST = 40.0
NITRO_REGEN = 3.2          # per second
NITRO_DURATION = 2.1
NITRO_COOLDOWN = 0.55
NEAR_MISS_NITRO = 11.0

NEAR_MISS_CHAIN_WINDOW = 2.6
NEAR_MISS_BASE = 20
NEAR_MISS_STEP = 10
NEAR_MISS_MAX = 80

POWERUP_SPAWN_MIN = 8.0
POWERUP_SPAWN_MAX = 14.5
POWERUP_LIFETIME = 18.0

BOOST_TIME = 6.0
SLOWMO_TIME = 6.5
MULTIPLIER_TIME = 8.0

SCORE_SURVIVAL = 11.0
SCORE_PER_KMH = 0.085
NEAR_MISS_THRESHOLD = 6.4  # columns between car bodies; one lane over counts

# ---------------------------------------------------------------------------
# 256-colour palette (xterm indices). Everything degrades to 8 colours when
# the terminal does not support 256 colours; see terminal.py.
# ---------------------------------------------------------------------------
C = {
    # UI / chrome
    "ink": 233,
    "ink2": 234,
    "ink3": 235,
    "panel": 234,
    "panel_hi": 236,
    "shadow": 232,
    "border": 45,
    "border_dim": 30,
    "accent": 45,
    "accent2": 51,
    "accent3": 39,
    "gold": 220,
    "gold2": 214,
    "white": 255,
    "offwhite": 252,
    "silver": 250,
    "dim": 243,
    "dim2": 240,
    "dim3": 237,
    "red": 203,
    "red_hot": 196,
    "red_dark": 88,
    "green": 46,
    "green_dark": 22,
    "blue": 39,
    "blue_dark": 25,
    "purple": 171,
    "orange": 208,
    "yellow": 226,
    "cyan": 51,
    "magenta": 201,
    "pink": 205,

    # terrain
    "grass0": 22,
    "grass1": 64,
    "grass2": 58,
    "grass3": 100,
    "grass_dark": 22,
    "tree0": 22,
    "tree1": 28,
    "tree2": 34,
    "tree3": 40,
    "tree_trunk": 94,
    "rock": 243,
    "rock_dark": 240,
    "flower": 227,
    "post": 252,
    "post_red": 160,

    # asphalt
    "road0": 236,
    "road1": 237,
    "road2": 238,
    "road3": 239,
    "road_dark": 235,
    "road_wear": 235,
    "shoulder": 234,
    "line_white": 255,
    "line_dim": 250,
    "line_yellow": 226,
    "line_yellow2": 220,
    "arrow": 240,

    # vehicle / effects
    "tire": 232,
    "window": 17,
    "window_light": 24,
    "headlight": 227,
    "taillight": 196,
    "exhaust": 244,
    "skin": 223,
    "burn": 240,
}

# Vehicle paint jobs. `dark` is used for a 1px shadow edge, `light` for trim.
CAR_PALETTES = {
    "green":   {"body": 34,  "dark": 22,  "light": 46,  "window": 17},
    "forest":  {"body": 28,  "dark": 22,  "light": 40,  "window": 17},
    "blue":    {"body": 27,  "dark": 18,  "light": 39,  "window": 16},
    "navy":    {"body": 25,  "dark": 17,  "light": 33,  "window": 16},
    "white":   {"body": 255, "dark": 249, "light": 231, "window": 238},
    "silver":  {"body": 250, "dark": 243, "light": 255, "window": 238},
    "red":     {"body": 160, "dark": 88,  "light": 196, "window": 17},
    "crimson": {"body": 124, "dark": 88,  "light": 160, "window": 17},
    "yellow":  {"body": 220, "dark": 136, "light": 226, "window": 17},
    "orange":  {"body": 208, "dark": 166, "light": 214, "window": 17},
    "purple":  {"body": 129, "dark": 91,  "light": 171, "window": 17},
    "teal":    {"body": 37,  "dark": 30,  "light": 45,  "window": 17},
    "lime":    {"body": 118, "dark": 70,  "light": 154, "window": 17},
    "pink":    {"body": 205, "dark": 161, "light": 218, "window": 17},
    "maroon":  {"body": 88,  "dark": 52,  "light": 124, "window": 17},
}

PLAYER_PALETTE = {
    "body": 39, "dark": 31, "light": 51, "window": 16,
    "stripe": 231, "headlight": 227, "taillight": 196,
}

POWERUP_STYLE = {
    "health":  {"fill": 231, "edge": 196, "icon": 196, "glow": 203, "label": "HEALTH"},
    "shield":  {"fill": 17,  "edge": 51,  "icon": 51,  "glow": 45,  "label": "SHIELD"},
    "boost":   {"fill": 220, "edge": 130, "icon": 130, "glow": 226, "label": "BOOST"},
    "slow":    {"fill": 25,  "edge": 39,  "icon": 51,  "glow": 39,  "label": "SLOW-MO"},
    "multi":   {"fill": 90,  "edge": 201, "icon": 226, "glow": 201, "label": "x2 SCORE"},
}

# ---------------------------------------------------------------------------
# 3x5 pixel font
# ---------------------------------------------------------------------------
FONT_3X5 = {
    "A": ("010", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"),
    "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"),
    "F": ("111", "100", "110", "100", "100"),
    "G": ("011", "100", "101", "101", "011"),
    "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"),
    "J": ("001", "001", "001", "101", "010"),
    "K": ("101", "101", "110", "101", "101"),
    "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"),
    "N": ("101", "111", "111", "111", "101"),
    "O": ("010", "101", "101", "101", "010"),
    "P": ("110", "101", "110", "100", "100"),
    "Q": ("010", "101", "101", "111", "011"),
    "R": ("110", "101", "110", "101", "101"),
    "S": ("011", "100", "010", "001", "110"),
    "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"),
    "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"),
    "Z": ("111", "001", "010", "100", "111"),
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"),
    "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "110", "001", "110"),
    "6": ("011", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "110"),
    " ": ("000", "000", "000", "000", "000"),
    "!": ("010", "010", "010", "000", "010"),
    ".": ("000", "000", "000", "000", "010"),
    ",": ("000", "000", "000", "010", "100"),
    ":": ("000", "010", "000", "010", "000"),
    "-": ("000", "000", "111", "000", "000"),
    "+": ("000", "010", "111", "010", "000"),
    "/": ("001", "001", "010", "100", "100"),
    "?": ("110", "001", "010", "000", "010"),
    "'": ("010", "010", "000", "000", "000"),
    "(": ("001", "010", "010", "010", "001"),
    ")": ("100", "010", "010", "010", "100"),
    "[": ("011", "010", "010", "010", "011"),
    "]": ("110", "010", "010", "010", "110"),
    "*": ("000", "101", "010", "101", "000"),
    "=": ("000", "111", "000", "111", "000"),
    "_": ("000", "000", "000", "000", "111"),
    ">": ("100", "010", "001", "010", "100"),
    "<": ("001", "010", "100", "010", "001"),
    "x": ("000", "101", "010", "101", "000"),
}

TITLE = "TERMINAL RUSH"
TAGLINE = "ENDLESS HIGHWAY SURVIVAL"
