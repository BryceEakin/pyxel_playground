import pyxel
import importlib
from datetime import datetime
import os

FILE_UPDATE_CHECK_FREQUENCY = 1 # in seconds
RELOAD_DELAY_AFTER_MODIFICATION = 1 # in seconds

class DebugManager():
    def __init__(self):
        self._loaded_assets = []
        self._file_modified_times = {}

        self.__run = pyxel.run
        pyxel.run = self._run_child
        
        self.__load = pyxel.load
        pyxel.load = self._load_child

        self.__init = pyxel.init
        pyxel.init = self._init_child

        self._last_check = datetime.now()
        self._prev_init_params = None

        self._is_running = False
        self._has_inited = False
        self._needs_to_run = False
        
        self._has_loaded_music = False

        self.game = importlib.import_module('game')
        assert 'game' in self.__dict__ and self.game is not None, "Game not loaded?  THE FUCK???!?"

        self._file_modified_times[self.game.__file__] = os.path.getmtime(self.game.__file__)
        self._has_inited = True

        if self._needs_to_run:
            print("And.... we're.... running!!!!")
            self._run_child(self._child_update, self._child_draw)

    def _init_child(self,
                    width,
                    height,
                    caption=pyxel.DEFAULT_CAPTION,
                    scale=pyxel.DEFAULT_SCALE,
                    palette=pyxel.DEFAULT_PALETTE,
                    fps=pyxel.DEFAULT_FPS,
                    border_width=pyxel.DEFAULT_BORDER_WIDTH,
                    border_color=pyxel.DEFAULT_BORDER_COLOR,
                    quit_key=pyxel.DEFAULT_QUIT_KEY):
        init_params = (width, height, caption, scale, palette, fps, border_width, border_color, quit_key)

        if self._prev_init_params is not None:
            if init_params != self._prev_init_params:
                print("Initialization parameters changed -- can't reload with updated code!  Quitting.")
                raise Exception("Initialization parameters changed")
            return

        self._prev_init_params = init_params
        self.__init(
            width, 
            height, 
            caption=caption, 
            scale=scale, 
            palette=palette, 
            fps=fps, 
            border_width=border_width, 
            border_color=border_color,
            quit_key=quit_key)

    def _needs_reload(self, file):
        f_modified = os.path.getmtime(file)
        if file not in self._file_modified_times:
            self._file_modified_times[file] = f_modified
            return False
        
        if (f_modified > self._file_modified_times[file] 
            and (datetime.now().timestamp() - f_modified) >= RELOAD_DELAY_AFTER_MODIFICATION
            ):
            return True
        return False

    def _load_child(self, filename: str, image=True, tilemap=True, sound=True, music=True):

        if self._has_loaded_music:
            music = False

        self._loaded_assets.append((filename, image, tilemap, sound, music))
        self._file_modified_times[filename] = os.path.getmtime(filename)

        if music:
            self._has_loaded_music = True

        print(f"Loading asset: {filename}")

        return self.__load(*self._loaded_assets[-1])

    def _run_child(self, update, draw):
        self._child_draw = draw
        self._child_update = update

        if not self._is_running and self._has_inited:
            self.__run(self.update, self.draw)
            self._is_running = True
            self._needs_to_run = False

        elif not self._has_inited:
            self._needs_to_run = True

    def draw(self):
        self._child_draw()
        
        pyxel.text(5, pyxel.height - pyxel.FONT_HEIGHT - 2, "DEBUG MODE", 7)

    def update(self):
        if (datetime.now() - self._last_check).total_seconds() > FILE_UPDATE_CHECK_FREQUENCY:
            if self._needs_reload(self.game.__file__):
                self._loaded_assets.clear()
                print("Reloading game file!")
                self.game = importlib.reload(self.game)
                self._file_modified_times[self.game.__file__] = os.path.getmtime(self.game.__file__)
            else:
                for asset_def in self._loaded_assets:
                    if self._needs_reload(asset_def[0]):
                        print(f"Reloading {asset_def[0]}!")
                        fn, img, tm, snd, mus = asset_def
                        #mus = False
                        self.__load(fn, img, tm, snd, mus)
                        self._file_modified_times[asset_def[0]] = os.path.getmtime(asset_def[0])
            self._last_check = datetime.now()

        self._child_update()

debug_app = DebugManager()

