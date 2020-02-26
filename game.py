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
SKY_SPRITE =        (0,  0, 88, 160, 32, -1)
MOUNTAIN_SPRITE =   (0,  0, 64, 160, 24, 12)
FOREST_SPRITE =     (0,  0, 48, 160, 16, 12)
FAR_CLOUD_SPRITE =  (0, 64, 32, 32,   8, 12)
NEAR_CLOUD_SPRITE = (0,  0, 32, 56,   8, 12)

# Foreground Sprites
FLOOR_SPRITE = (0, 0, 16, 40, 8, 12)
FRUIT_SPRITE = [
    (0, 32, 0, 16, 16, 12),
    (0, 48, 0, 16, 16, 12),
    (0, 64, 0, 16, 16, 12)
]
PLAYER_SPRITE = [
    (0,  0, 0, -16, 16, 12,),  # Player when falling
    (0, 16, 0, -16, 16, 12,),  # Player when jumping
]

# Some level "themes" of blocks and ladders
class LevelTheme():
    def __init__(self, theme_idx):
        y = 16*theme_idx

        self.block_1x = (1, 0, y, 16, 16, -1)
        self.block_4x = (1, 0, y, 64, 16, -1)
        self.ladder_top = (1, 64, y, 16, 16, -1)
        self.ladder = (1, 64, y, 16, 16, -1)

    def draw_blocks(self, x,y, draw_w, draw_h):
        img, u, v, w, h, colkey = self.block_4x

        w = min(draw_w, w)
        h = min(draw_h, h)

        pyxel.blt(x, y, img, u, v, w, h, colkey)

THEME_ZIG_ZAG = LevelTheme(0)
THEME_GOLD_BLOCKS = LevelTheme(1)
THEME_BRICKS = LevelTheme(2)
THEME_GRASS = LevelTheme(3)

THEMES = [LevelTheme(i) for i in range(4)]

BASE_FPS = 30


class App:
    def __init__(self, fps=BASE_FPS, speed=1.0):
        pyxel.init(160, 120, caption="Pyxel Jump", fps=fps)

        # Load all the images and sounds used in the game
        pyxel.load("assets/jump_game.pyxres")

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
        self.player_y = -16
        self.player_vy = 0
        self.player_is_alive = True

        # Define the stuff on screen
        self.far_cloud = [(-10, 75), (40, 65), (90, 60)]
        self.near_cloud = [(10, 25), (70, 35), (120, 15)]
        self.floor = [(i * 60, randint(32, 104), True) for i in range(4)]
        self.fruit = [(i * 60, randint(40, 104), randint(0, 2), True) for i in range(4)]

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

        for i, v in enumerate(self.floor):
            self.floor[i] = self.update_floor(*v)

        for i, v in enumerate(self.fruit):
            self.fruit[i] = self.update_fruit(*v)

    def update_player(self):
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.GAMEPAD_1_LEFT):
            self.player_x = max(self.player_x - 2 * self._frame_step, 0)

        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.GAMEPAD_1_RIGHT):
            self.player_x = min(self.player_x + 2 * self._frame_step, pyxel.width - 16)

        self.player_y += self.player_vy * self._frame_step
        self.player_vy = min(self.player_vy + self._frame_step, 8)

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

    def update_floor(self, x, y, is_active):
        if is_active:
            if (
                self.player_x + 16 >= x
                and self.player_x <= x + 40
                and self.player_y + 16 >= y
                and self.player_y <= y + 8
                and self.player_vy > 0
            ):
                is_active = False
                self.score += 10
                self.player_vy = -10
                pyxel.play(3, 3)
        else:
            y += 6 * self._frame_step

        x -= 4 * self._frame_step

        if x < -40:
            x += 240
            y = randint(40, 104)
            is_active = True

        return x, y, is_active

    def update_fruit(self, x, y, kind, is_active):
        if is_active and abs(x - self.player_x) < 12 and abs(y - self.player_y) < 12:
            is_active = False
            self.score += (kind + 1) * 100
            self.player_vy = min(self.player_vy, -8)
            pyxel.play(3, 4)

        x -= 2 * self._frame_step

        if x < -40:
            x += 240
            y = randint(32, 104)
            kind = randint(0, 2)
            is_active = True

        return (x, y, kind, is_active)

    def draw(self):
        pyxel.cls(12)

        # draw sky
        pyxel.blt(0, 88, *SKY_SPRITE)

        # draw mountain
        pyxel.blt(0, 88, *MOUNTAIN_SPRITE)

        frame_steps = math.floor(self.frame_count * self._frame_step)

        # draw forest
        offset = frame_steps % 160
        for i in range(2):
            pyxel.blt(i * 160 - offset, 104, *FOREST_SPRITE)

        # draw clouds
        offset = (frame_steps // 16) % 160
        for i in range(2):
            for x, y in self.far_cloud:
                pyxel.blt(x + i * 160 - offset, y, *FAR_CLOUD_SPRITE)

        offset = (frame_steps // 8) % 160
        for i in range(2):
            for x, y in self.near_cloud:
                pyxel.blt(x + i * 160 - offset, y, *NEAR_CLOUD_SPRITE)

        # draw floors
        for idx, (x, y, _is_active) in enumerate(self.floor):
            THEMES[idx].draw_blocks(x, y, 40, 8)
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
