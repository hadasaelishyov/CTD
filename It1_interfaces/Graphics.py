import pathlib
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import copy
import glob
from img import Img
from Command import Command



class Graphics:
    def __init__(self,
                 sprites_folder: pathlib.Path,
                 cell_size: tuple[int, int],
                 loop: bool = True,
                 fps: float = 6.0):
        self.sprites_folder = sprites_folder
        self.cell_size = cell_size
        self.loop = loop
        self.fps = fps
        self.sprites = []
        self.frame_duration_ms = int(1000 / fps)
        self.current_frame = 0
        self.start_time_ms = 0
        self.current_command = None
        self._load_sprites()

    def _load_sprites(self):

        if not self.sprites_folder.exists():
            return
            
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp']
        sprite_files = []
        
        for ext in extensions:
            sprite_files.extend(glob.glob(str(self.sprites_folder / ext)))
        
        sprite_files.sort()  # Ensure consistent ordering
        
        for sprite_file in sprite_files:
            try:
                sprite = Img().read(sprite_file, size=self.cell_size, keep_aspect=True)
                self.sprites.append(sprite)
            except Exception as e:
                print(f"Failed to load sprite {sprite_file}: {e}")
        
        # If no sprites found, create a default colored square
        if not self.sprites:
            import numpy as np
            default_img = Img()
            default_img.img = np.full((self.cell_size[1], self.cell_size[0], 4), 
                                    [100, 100, 255, 255], dtype=np.uint8)
            self.sprites.append(default_img)

    def copy(self):
        new_graphics = Graphics(self.sprites_folder, self.cell_size, self.loop, self.fps)
        new_graphics.sprites = self.sprites.copy()
        new_graphics.current_frame = self.current_frame
        new_graphics.start_time_ms = self.start_time_ms
        new_graphics.current_command = self.current_command
        return new_graphics

    def reset(self, cmd: Command):
        self.current_command = cmd
        self.start_time_ms = cmd.timestamp
        self.current_frame = 0

    def update(self, now_ms: int):
        if not self.sprites or self.start_time_ms == 0:
            return
        elapsed_ms = now_ms - self.start_time_ms
        frame_index = int(elapsed_ms / self.frame_duration_ms)
        
        if self.loop:
            self.current_frame = frame_index % len(self.sprites)
        else:
            self.current_frame = min(frame_index, len(self.sprites) - 1)

    def get_img(self) -> Img:

        if not self.sprites:
            empty_img = Img()
            import numpy as np
            empty_img.img = np.zeros((self.cell_size[1], self.cell_size[0], 4), dtype=np.uint8)
            return empty_img
            
        return self.sprites[self.current_frame]