import pathlib

from Graphics import Graphics


class GraphicsFactory:
    def load(self,
             sprites_dir: pathlib.Path,
             cfg: dict,
             cell_size: tuple[int, int]) -> Graphics:
        loop = cfg.get('loop', True) if cfg else True
        fps = cfg.get('fps', 6.0) if cfg else 6.0
        
        return Graphics(sprites_dir, cell_size, loop, fps)