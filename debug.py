import pyxel
import importlib

class DebugManager():
    def __init__(self):
        self.__run = pyxel.run
        pyxel.run = self._run_child
        
        self.__load = pyxel.load
        self._loaded_assets = []

    def _load_child(filename: str, image=True, tilemap=True, sound=True, music=True):
        self._loaded_assets.append((filename, image, tilemap, sound, music))
        return self.__load(*self._loaded_assets[-1])

    def _run_child(self, draw, update):
        self._child_draw = draw
        self._child_update = update

        return self.__run(self.update, self.draw)

    def draw(self):
        self._child_draw()
        
        pyxel.text(5, pyxel.height - pyxel.FONT_HEIGHT - 2, "DEBUG MODE", 7)

    def update(self):
        self._child_update()

debug_app = DebugManager()

import game
