import argparse
import math
from random import randint

import pyxel

# sprite definitions are just pieces of the image(s) in the .pyxres file
# look at it in the editor to see what I mean
# - image number in the .pyxres file with the images (currently always 0)
# - x coordinate in the source image to start at
# - y coordinate in the source image
# - width of the piece to grab
# - height of the piece to grab
# - [optional] what color to make transparent (-1 means no transparency)

# Background Sprites

# Foreground Sprites
FLOOR_SPRITE = (0, 0, 16, 40, 8, 12)
FRUIT_SPRITE = [
    (0, 32, 0, 16, 16, 12),
    (0, 48, 0, 16, 16, 12),
    (0, 64, 0, 16, 16, 12),
    (0, 80, 0, 16, 16, 12)
]
PLAYER_SPRITE = [
    (0,  0, 0, 16, 16, 12,),  # Player when falling
    (0, 16, 0, 16, 16, 12,),  # Player when jumping
]

BLOCK_SIZE = 16

# Some level "themes" of blocks and ladders
class LevelTheme():
    def __init__(self, theme_idx):
        y = 16*theme_idx

        self.block_1x = (1, 0, y, 16, 16, -1)
        self.block_4x = (1, 0, y, 64, 16, -1)
        self.ladder_top = (1, 64, y, 16, 16, -1)
        self.ladder = (1, 64, y, 16, 16, -1)

    def draw_blocks(self, x, y, draw_w, draw_h):
        img, u, v, w, h, colkey = self.block_4x

        for x_offset in range(0, draw_w, 48):
            for y_offset in range(0, draw_h, 16):
                w = min(draw_w - x_offset, 48)
                h = min(draw_h - y_offset, 16)

                pyxel.blt(x + x_offset, y + y_offset, img, u, v, w, h, colkey)

THEME_ZIG_ZAG = LevelTheme(0)
THEME_GOLD_BLOCKS = LevelTheme(1)
THEME_BRICKS = LevelTheme(2)
THEME_GRASS = LevelTheme(3)
THEME_MASONRY = LevelTheme(4)

THEMES = [LevelTheme(i) for i in range(5)]

BASE_FPS = 30

class Floor:
    def __init__(self, floor_x, floor_y, is_active, floor_width=40, floor_height=8, theme=None):
        self.floor_x = int(floor_x) * BLOCK_SIZE
        self.floor_y = int(floor_y) * BLOCK_SIZE
        self.floor_width = int(floor_width) * BLOCK_SIZE
        self.floor_height = min(self.floor_width, int(floor_height) * BLOCK_SIZE)
        self.theme = theme
        self.is_active = is_active

    @property
    def left(self):
        return self.floor_x

    @property
    def right(self):
        return self.floor_x + self.floor_width

    @property
    def top(self):
        return self.floor_y

    @property
    def bottom(self):
        return self.floor_y + self.floor_height


class App:
    def __init__(self, fps=BASE_FPS, speed=1.0):
        pyxel.init(256, 256, caption="Pyxel Toomy", fps=fps)

        # Load all the images and sounds used in the game
        pyxel.load("assets/toomy_game.pyxres")

        self.__speed = speed
        self._fps = fps

        # Factor to keep things running normally at different fps / speeds
        self._frame_step = speed * BASE_FPS / fps

        # number of frames that would have happened so far at current speed/fps
        # (adjusted when speed changes to keep things rendering at the same spot)
        self.frame_count = 0

        # Seconds of 1x-speed game time since game start
        self.game_time = 0.0

        # Player info
        self.score = 0
        self.player_x = 72
        self.player_y = 25
        self.player_vy = 0
        self.player_is_alive = True

        # Define the stuff on screen
        self.far_cloud = [(-10, 75), (40, 65), (90, 60)]
        self.near_cloud = [(10, 25), (70, 35), (120, 15)]
        self.floor = [
            Floor(
                randint(0, 200//BLOCK_SIZE),
                randint(8, 16),
                True,
                randint(1, 10),
                1
            ) for i in range(5)]
        self.fruit = [(i * 60, randint(40, 104), randint(0, 3), True) for i in range(5)]

        # Start playing music (sound #0)
        pyxel.playm(0, loop=True)

        # Run the game (update/draw loop)
        pyxel.run(self.update, self.draw)

    @property
    def _speed(self):
        return self.__speed

    @_speed.setter
    def _speed(self, newval):
        # When speed changes we have to update the frame counter or background things
        # will suddenly jump around

        ratio = newval/self.__speed
        self.frame_count /= ratio
        self._frame_step *= ratio
        self.__speed = newval

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        if pyxel.btnp(pyxel.KEY_EQUAL):
            self._speed = min(3.0, self._speed + 0.25)
        elif pyxel.btnp(pyxel.KEY_MINUS):
            self._speed = max(0.25, self._speed - 0.25)

        self.frame_count += self._frame_step
        self.game_time += self._speed/self._fps

        self.update_player()

        for i, v in enumerate(self.fruit):
            self.fruit[i] = self.update_fruit(*v)

    def update_player(self):
        delta_x = 0
        delta_y = 0

        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.GAMEPAD_1_LEFT):
            delta_x = self._frame_step * -2

        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.GAMEPAD_1_RIGHT):
            delta_x = self._frame_step * 2

        if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.GAMEPAD_1_UP):
            self.player_vy = -10

        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.GAMEPAD_1_DOWN):
            delta_y = self._frame_step * 2

        delta_y += self.player_vy * self._frame_step

        x_valid, y_valid = self.validate_movement(delta_x, delta_y)

        if x_valid:
            self.player_x += delta_x

        if y_valid:
            self.player_y += delta_y
            self.player_vy += self._frame_step
        else:
            self.player_vy = 0

        if self.player_y > pyxel.height:
            if self.player_is_alive:
                self.player_is_alive = False
                pyxel.play(3, 5)

            if self.player_y > 600:
                self.score = 0
                self.player_x = 72
                self.player_y = -16
                self.player_vy = 0
                self.player_is_alive = True

    def validate_movement(self, delta_x, delta_y):
        x_valid = True
        y_valid = True

        for floor in self.floor:
            if (
                self.player_x + 16 + delta_x >= floor.left
                and self.player_x + delta_x <= floor.right

                and self.player_y + 16 >= floor.top
                and self.player_y <= floor.bottom
            ):
                x_valid = False

            if x_valid:
                if (
                    self.player_x + 16 + delta_x >= floor.left
                    and self.player_x + delta_x <= floor.right

                    and self.player_y + 16 + delta_y >= floor.top
                    and self.player_y + delta_y <= floor.bottom
                ):
                    y_valid = False

            else:
                if (
                    self.player_x + 16 >= floor.left
                    and self.player_x <= floor.right

                    and self.player_y + 16 + delta_y >= floor.top
                    and self.player_y + delta_y <= floor.bottom
                ):
                    y_valid = False

        return x_valid, y_valid

    def update_fruit(self, x, y, kind, is_active):
        if is_active and abs(x - self.player_x) < 12 and abs(y - self.player_y) < 12:
            is_active = False
            self.score += (kind + 1) * 100
            self.player_vy = min(self.player_vy, -8)
            pyxel.play(3, 4)

        # x -= 2 * self._frame_step

        if x < -40:
            x += 240
            y = randint(32, 104)
            kind = randint(0, 3)
            is_active = True

        return (x, y, kind, is_active)

    def draw(self):
        pyxel.cls(12)


        # draw floors
        for idx, floor in enumerate(self.floor):
            THEMES[idx].draw_blocks(floor.left, floor.top, floor.floor_width, floor.floor_height)
            #pyxel.blt(x, y, *FLOOR_SPRITE)

        # draw fruits
        for x, y, kind, is_active in self.fruit:
            if is_active:
                pyxel.blt(x, y, *FRUIT_SPRITE[kind])

        # draw player
        pyxel.blt(self.player_x, self.player_y, *PLAYER_SPRITE[1 if self.player_vy > 0 else 0])

        # draw score
        s = "SCORE {:>4}".format(self.score)
        pyxel.text(5, 4, s, 1)
        pyxel.text(4, 4, s, 7)

        # draw time
        t = self.game_time
        t = f"{int(t//60)}:{t%60:04.1f}"
        pyxel.text(pyxel.width - 4 - 4*len(t), 4, t, 1)
        pyxel.text(pyxel.width - 5 - 4*len(t), 4, t, 7)

        # draw current speed
        s = f"SPEED {self._speed:0.2f}x"
        pyxel.text(pyxel.width - 4 - 4*len(s), 11, s, 1)
        pyxel.text(pyxel.width - 5 - 4*len(s), 11, s, 7)


parser = argparse.ArgumentParser()

parser.add_argument('--fps', default=75, type=int)
parser.add_argument('--speed', default=1.0, type=float)

args = parser.parse_args()

App(fps=args.fps, speed=args.speed)
