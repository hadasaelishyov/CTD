
# mock_img.py
from img import Img
import numpy as np

class MockImg(Img):
    traj     : list[tuple[int,int]]  = []   # every draw_on() position
    txt_traj : list[tuple[tuple[int,int],str]] = []

    def __init__(self):                     # override, no cv2 needed
        super().__init__()
        self.img = np.zeros((800, 800, 4), dtype=np.uint8)

    # keep the method names identical to Img -------------------------
    def read(self, path, *_, **__):
        return self

    def draw_on(self, other, x, y):
        self.traj.append((x, y))

    def put_text(self, txt, x, y, font_size, *_, **__):
        self.txt_traj.append(((x, y), txt))

    def show(self): 
        pass

    # helper for tests
    @classmethod
    def reset(cls):
        cls.traj.clear()
        cls.txt_traj.clear()
