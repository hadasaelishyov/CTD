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
        """טעינת חוקי התנועה מהקובץ"""
        try:
            with open(self.txt_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        try:
                            # תיקון: טיפול בפורמטים שונים
                            parts = line.split(",")
                            if len(parts) >= 2:
                                dx = int(parts[0].strip())
                                dy = int(parts[1].strip())
                                self.rules.append((dx, dy))
                        except ValueError as e:
                            print(f"Warning: Invalid move format at line {line_num}: '{line}' - {e}")
                            continue
        except FileNotFoundError:
            print(f"Warning: Moves file not found: {self.txt_path}")
            # ברירת מחדל: תנועות בסיסיות
            self.rules = [(0,1), (0,-1), (1,0), (-1,0)]  # up, down, right, left
        except Exception as e:
            print(f"Error loading moves from {self.txt_path}: {e}")
            self.rules = [(0,1), (0,-1), (1,0), (-1,0)]

    def get_moves(self, r: int, c: int) -> List[Tuple[int, int]]:
        """קבלת כל המהלכים האפשריים ממיקום נתון"""
        moves = []
        for dx, dy in self.rules:
            nr, nc = r + dy, c + dx  # תיקון: dy לשורה, dx לעמודה
            if 0 <= nr < self.board_height and 0 <= nc < self.board_width:
                moves.append((nr, nc))
        return moves

    def can_move_to(self, from_r: int, from_c: int, to_r: int, to_c: int) -> bool:
        """בדיקה האם מהלך מסוים חוקי"""
        possible_moves = self.get_moves(from_r, from_c)
        return (to_r, to_c) in possible_moves

    def get_move_vector(self, from_r: int, from_c: int, to_r: int, to_c: int) -> Tuple[int, int]:
        """קבלת וקטור התנועה בין שתי נקודות"""
        return (to_r - from_r, to_c - from_c)

    def copy(self):
        """יצירת עותק של אובייקט המהלכים"""
        new_moves = Moves.__new__(Moves)
        new_moves.board_height = self.board_height
        new_moves.board_width = self.board_width
        new_moves.txt_path = self.txt_path
        new_moves.dims = self.dims
        new_moves.rules = self.rules.copy()
        return new_moves