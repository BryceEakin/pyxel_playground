import argparse
import math
from random import randint
import os
import itertools

import arcade

# change active dir to assets
ASSET_PATH = os.path.join(os.path.dirname(__file__), 'assets')

# sprite definitions are just pieces of the image(s) in the .pyxres file
# look at it in the editor to see what I mean
# - image number in the .pyxres file with the images (currently always 0)
# - x coordinate in the source image to start at
# - y coordinate in the source image
# - width of the piece to grab
# - height of the piece to grab
# - [optional] what color to make transparent (-1 means no transparency)

# Global Parameters
SCREEN_HEIGHT = 256
SCREEN_WIDTH = 256

MIN_BEZEL = 10

# Foreground Sprites
FRUIT_SPRITES = f"{ASSET_PATH}/Fruits.png"
PLAYER_SPRITES = [
    f"{ASSET_PATH}/Player_Landed.png",
    f"{ASSET_PATH}/Player_Jumping.png",
]
BLOCK_SPRITES = f"{ASSET_PATH}/Blocks.png"

BLOCK_SIZE = 16

# Some level "themes" of blocks and ladders
THEME_ZIG_ZAG = 0
THEME_GOLD_BLOCKS = 1
THEME_BRICKS = 2
THEME_GRASS = 3
THEME_MASONRY = 4
from collections import defaultdict

# Create a theme lookup dynamically from the constants above
THEMES = {name: value for name, value in globals().items() if name.startswith("THEME_")}

GOING_LEFT = 0
GOING_RIGHT = 2
LANDED = 0
JUMPING = 1

class Floor(arcade.Sprite):
    def __init__(self, theme_idx, floor_x, floor_y, floor_width=1, floor_height=1):
        super().__init__(
            BLOCK_SPRITES, 
            image_x = 0, 
            image_y = theme_idx * 16,
            image_width = min(floor_width * BLOCK_SIZE, 64),
            image_height = min(floor_height * BLOCK_SIZE, 16)
        )

        self.left = int(floor_x) * BLOCK_SIZE
        self.top = int(floor_y) * BLOCK_SIZE
        self.width = int(floor_width) * BLOCK_SIZE
        self.height = int(floor_height) * BLOCK_SIZE


def create_floor_sprites(theme_idx, x, y, width, height):
    width = int(width)
    height = min(int(width), int(height))

    assert width > 0 and height > 0, "width and height must be positive!"

    if width <= 4 and height == 1:
        return [Floor(theme_idx, x, y, width, height)]

    result = []

    for x_offset in range(0, width, 4):
        for y_offset in range(0, height, 1):
            w = min(width - x_offset, 4)
            h = min(height - y_offset, 1)

            result.append(Floor(theme_idx, x + x_offset, y + y_offset, w, h))
    
    return result

class Fruit(arcade.Sprite):
    def __init__(self, x, y, type):
        super().__init__(
            FRUIT_SPRITES,
            image_x=0 + 16*type,
            image_y=0,
            image_width=16,
            image_height=16
        )

        self.center_x = x
        self.center_y = y
        self.type = type

class Player(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.center_x = x
        self.center_y = y

        self.append_texture(arcade.load_texture(PLAYER_SPRITES[0], mirrored=False))
        self.append_texture(arcade.load_texture(PLAYER_SPRITES[1], mirrored=False))
        self.append_texture(arcade.load_texture(PLAYER_SPRITES[0], mirrored=True))
        self.append_texture(arcade.load_texture(PLAYER_SPRITES[1], mirrored=True))

        self._is_going_right = True
        self._is_jumping = True

        self.set_texture(GOING_RIGHT + JUMPING)

    def handle_key_press(self, key, modifiers):
        if key == arcade.key.LEFT:
            self.change_x = -2
            self._is_going_right = True
            
        elif key == arcade.key.RIGHT:
            self.change_x = 2
            self._is_going_right = False
        
        elif key == arcade.key.UP:
            self.change_y = 10
            self._is_jumping = True

        new_texture = (
            (GOING_RIGHT if self._is_going_right else GOING_LEFT)
            + (JUMPING if self._is_jumping else LANDED)
        )

        self.set_texture(new_texture)

    def handle_key_release(self, key, modifiers):
        if key in (arcade.key.LEFT, arcade.key.RIGHT):
            self.change_x = 0

    def handle_collisions(self, collisions, delta_time):
        delta_x, delta_y = self.change_x, self.change_y

        hit_x, hit_y = False, False

        def recheck_collisions():
            return [x for x in collisions if arcade.check_for_collision(x, self)]

        self.center_x -= delta_x
        # collection of hits moving only along the y axis
        y_hits = recheck_collisions()
        self.center_x += delta_x

        self.center_y -= delta_y
        # collection of hits moving only along the x axis
        x_hits = recheck_collisions()
        self.center_y += delta_y

        if y_hits:
            self.change_y = 0
            if delta_y > 0:
                self.top = min(h.bottom for h in y_hits)
            else:
                self.bottom = max(h.top for h in y_hits)
                is_jumping=False
                self.set_texture((GOING_RIGHT if self._is_going_right else GOING_LEFT) + LANDED)
                
        if x_hits:
            self.change_x = 0
            if delta_x > 0:
                self.right = min(h.left for h in x_hits)
            else:
                self.left = max(h.right for h in x_hits)
    
    def update(self):
        if self._is_jumping or self.change_x != 0.0:
            pass # Add logic to check if we can fall some

        self.center_y += self.change_y
        self.center_x += self.change_x

        self.change_y -= 0.5

class App(arcade.Window):
    is_key_pressed = defaultdict(lambda x: False)

    def __init__(self, speed=1.0, fps=60):
        super().__init__(
            SCREEN_WIDTH * 2 + MIN_BEZEL * 2, 
            SCREEN_HEIGHT * 2 + MIN_BEZEL * 2, 
            title="Pyxel Toomy", 
            update_rate=1.0 / fps, 
            antialiasing=True,
            resizable=True
        )

        self._x_bezels = MIN_BEZEL
        self._y_bezels = MIN_BEZEL

        self.__speed = speed
        self._fps = fps

        # Factor to keep things running normally at different fps / speeds
        self._frame_step = speed

        # number of frames that would have happened so far at current speed/fps
        # (adjusted when speed changes to keep things rendering at the same spot)
        self.frame_count = 0

        # Seconds of 1x-speed game time since game start
        self.game_time = 0.0

        # Player info
        self.score = 0
        self.player = None
        self.player_is_alive = True

        # Define the stuff on screen
        self.floors = None

        self.background = None

        arcade.set_background_color(arcade.color.CORNFLOWER_BLUE)
        self.set_minimum_size(SCREEN_WIDTH, SCREEN_HEIGHT)
        

    def setup(self):
        self.player = Player(72, SCREEN_HEIGHT-10)
        self.floors = arcade.SpriteList(use_spatial_hash = True)
        self.floors.extend(
            itertools.chain(
                *[
                    create_floor_sprites(
                        i, 
                        randint(0, 14),
                        randint(0,12),
                        randint(1,10),
                        randint(1,4)
                    ) for i in range(5)
                ]
            )
        )

        self.fruits = arcade.SpriteList(use_spatial_hash = True)
        self.fruits.extend(
            [Fruit(randint(5,250), randint(20, 200), randint(0,3)) for i in range(5)]
        )

        print(f"Created {len(self.floors)} floor sprites!")

        self.background = arcade.load_texture(":resources:images/backgrounds/abstract_1.jpg")

    def on_resize(self, w, h):
        orig_w, orig_h = w, h

        w -= MIN_BEZEL * 2
        h -= MIN_BEZEL * 2

        scale = min(
            w / SCREEN_WIDTH,
            h / SCREEN_HEIGHT
        )

        self._x_bezels = int((orig_w/scale - SCREEN_WIDTH)/2)+1
        self._y_bezels = int((orig_h/scale - SCREEN_HEIGHT)/2)+1

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

    def on_key_press(self, key, modifiers):
        print(f"Key pressed!: {key}, {modifiers}")

        if key == arcade.key.ESCAPE:
            arcade.quit()
        if key == arcade.key.R:
            print("Resetting the game!!!")
            self.setup()
        if key in {arcade.key.EQUAL, arcade.key.NUM_ADD}:
            print("Speeding up!")
            self._speed = min(3.0, self._speed + 0.25)
        if key in {arcade.key.MINUS, arcade.key.NUM_SUBTRACT}:
            print("Slowing down....")
            self._speed = max(0.25, self._speed - 0.25)
        
        App.is_key_pressed[key] = True

        self.player.handle_key_press(key, modifiers)
    
    def on_key_release(self, key, modifiers):
        self.player.handle_key_release(key, modifiers)
        App.is_key_pressed[key] = False

    def on_update(self, delta_time):
        self.frame_count += self._frame_step * delta_time
        self.game_time += delta_time

        self.player.update()

        # See if they hit a floor
        collisions = arcade.check_for_collision_with_list(self.player, self.floors)
        if collisions:
            self.player.handle_collisions(collisions, delta_time)

        # See if they hit a fruit
        collisions = arcade.check_for_collision_with_list(self.player, self.fruits)
        for fruit in collisions:
            if fruit in self.fruits:
                self.fruits.remove(fruit)
                self.score += (fruit.type + 1) * 100


        self.check_for_player_death()

        # for i, v in enumerate(self.fruit):
        #     self.fruit[i] = self.update_fruit(*v)

    def check_for_player_death(self):
        if self.player.top < 0:
            if self.player_is_alive:
                self.player_is_alive = False
                #pyxel.play(3, 5)

            if self.player.top < -100:
                self.score = 0
                self.player.center_x = 72
                self.player.center_y = SCREEN_HEIGHT + 16
                self.player.change_y = 0
                self.player_is_alive = True

    def update_fruit(self, x, y, kind, is_active):
        if is_active and abs(x - self.player_x) < 12 and abs(y - self.player_y) < 12:
            is_active = False
            self.score += (kind + 1) * 100
            self.player_vy = min(self.player_vy, -8)
            #pyxel.play(3, 4)

        # x -= 2 * self._frame_step

        if x < -40:
            x += 240
            y = randint(32, 104)
            kind = randint(0, 3)
            is_active = True

        return (x, y, kind, is_active)

    def on_draw(self):
        # Required before we start drawing
        arcade.start_render()
        arcade.set_viewport(
            -self._x_bezels, SCREEN_WIDTH-1 + self._x_bezels, 
            -self._y_bezels, SCREEN_HEIGHT-1 + self._y_bezels
        )

        # draw background
        arcade.draw_lrwh_rectangle_textured(0, 0,
                                            SCREEN_WIDTH, SCREEN_HEIGHT,
                                            self.background,
                                            alpha=127)

        # draw sprites
        self.floors.draw()
        self.fruits.draw()
        self.player.draw()

        # draw score
        s = "SCORE {:>4}".format(self.score)
        arcade.draw_text(s, 5, SCREEN_HEIGHT - 12, arcade.color.WHITE, 8)
        #arcade.draw_text(s, 4, SCREEN_HEIGHT - 12, arcade.color.BLACK, 8)
        
        # draw time
        t = self.game_time
        t = f"{int(t//60)}:{t%60:04.1f}"
        arcade.draw_text(t, SCREEN_WIDTH - 4, SCREEN_HEIGHT - 12, arcade.color.WHITE, 8, anchor_x='right')
        #arcade.draw_text(t, SCREEN_WIDTH - 5, SCREEN_HEIGHT - 12, arcade.color.BLACK, 8, anchor_x='right')

        # draw current speed
        s = f"SPEED {self._speed:0.2f}x"
        arcade.draw_text(s, SCREEN_WIDTH - 4, SCREEN_HEIGHT - 21, arcade.color.WHITE, 8, anchor_x='right')
        #arcade.draw_text(s, SCREEN_WIDTH - 5 - 4*len(s), SCREEN_HEIGHT - 21, arcade.color.BLACK, 8)

        # draw the black bezels
        if self._x_bezels > 0:
            arcade.draw_lrtb_rectangle_filled(-self._x_bezels, 0, SCREEN_HEIGHT, 0, arcade.color.BLACK)
            arcade.draw_lrtb_rectangle_filled(SCREEN_WIDTH, SCREEN_WIDTH + self._x_bezels, SCREEN_HEIGHT, 0, arcade.color.BLACK)

        if self._y_bezels > 0:
            arcade.draw_lrtb_rectangle_filled(
                -self._x_bezels, 
                SCREEN_WIDTH + self._x_bezels, 
                0, 
                -self._y_bezels, 
                arcade.color.BLACK
            )
            arcade.draw_lrtb_rectangle_filled(
                -self._x_bezels, 
                SCREEN_WIDTH + self._x_bezels, 
                SCREEN_HEIGHT + self._y_bezels, 
                SCREEN_HEIGHT, 
                arcade.color.BLACK
            )

        # draw the frame buffer to the screen
        arcade.flip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--fps', default=75, type=int)
    parser.add_argument('--speed', default=1.0, type=float)

    args = parser.parse_args()
    
    game = App(fps=args.fps, speed=args.speed)
    game.setup()
    arcade.run()
