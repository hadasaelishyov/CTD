# Moves.py  – drop-in replacement
import pathlib
from typing import List, Tuple

class Moves:
   
    def __init__(self, txt_path: pathlib.Path, dims: Tuple[int, int]):
        self.board_height, self.board_width = dims
        self.txt_path = txt_path
        self.dims = dims
        self.rules = []
        self._load_rules()

    def _load_rules(self):
        with open(self.txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    dx, dy = map(int, line.split(","))
                    self.rules.append((dx, dy))


    def get_moves(self, r: int, c: int) -> List[Tuple[int, int]]:
        moves = []
        for dx, dy in self.rules:
            nr, nc = r + dy, c + dx
            if 0 <= nr < self.board_height and 0 <= nc < self.board_width:
                moves.append((nr, nc))
        return moves