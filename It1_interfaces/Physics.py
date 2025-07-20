from typing import Tuple, Optional
from Command import Command
from Board import Board  # Import the Board class
import math
class Physics:
    SLIDE_CELLS_PER_SEC = 4.0 

    def __init__(self, start_cell: Tuple[int, int], board: "Board", speed_m_s: float = 1.0):
        self.board = board
        self.speed_m_s = speed_m_s
        self.start_cell = start_cell
        self.current_cell = start_cell
        self.target_cell: Optional[Tuple[int, int]] = None
        self.start_time_ms: Optional[int] = None
        self.duration_ms: Optional[int] = None
        self.state = "Idle"
        self.cooldown_start_ms = 0
        self.cooldown_duration_ms = 0
        self.can_be_captured_flag = True
        self.can_capture_flag = True
        self.current_command = None

    def reset(self, cmd: Command):
        self.current_command = cmd
        self.start_time_ms = cmd.timestamp

        self.target_cell = None
        self.duration_ms = None
        
        if cmd.type == "Move" and len(cmd.params) >= 2:
            start_pos = self._parse_position(cmd.params[0])
            target_pos = self._parse_position(cmd.params[1])
            
            if start_pos and target_pos:
                self.current_cell = start_pos
                self.target_cell = target_pos
                
                distance = math.sqrt((target_pos[0] - start_pos[0])**2 + (target_pos[1] - start_pos[1])**2)
                self.duration_ms = int((distance / self.SLIDE_CELLS_PER_SEC) * 1000)
                self.state = "Moving"
                self.can_be_captured_flag = False
                
                # קוד השהיה אחרי הסיום
                self.cooldown_start_ms = cmd.timestamp + self.duration_ms
                self.cooldown_duration_ms = 2000  # 2 שניות כמו שביקשת
        
        elif cmd.type == "Jump":
            self.state = "Jumping"
            self.duration_ms = 1000  # שנייה אחת כמו שביקשת
            self.cooldown_start_ms = cmd.timestamp
            self.cooldown_duration_ms = 1000
            self.can_be_captured_flag = False  # במהלך קפיצה לא ניתן לאכול
            self.can_capture_flag = False  # במהלך קפיצה לא ניתן לאכול אחרים
    
    def _parse_position(self, pos_str: str) -> Optional[Tuple[int, int]]:
        if len(pos_str) != 2:
            return None
        
        col = ord(pos_str[0].lower()) - ord('a')
        row = int(pos_str[1]) - 1
        
        if 0 <= col < self.board.W_cells and 0 <= row < self.board.H_cells:
            return (row, col)
        return None

    def update(self, now_ms: int):
        if self.start_time_ms is None:
            return
            
        if self.state == "Moving" and self.current_command:
            elapsed_ms = now_ms - self.start_time_ms
            
            if elapsed_ms >= self.duration_ms:
                # תזוזה הסתיימה
                self.current_cell = self.target_cell
                self.state = "Idle"
                self.can_be_captured_flag = True
                self.can_capture_flag = True
            else:
                # עדיין בתזוזה - חישוב מיקום ביניים
                ratio = elapsed_ms / self.duration_ms
                r1, c1 = self.current_cell if hasattr(self.current_cell, '__iter__') else self.start_cell
                r2, c2 = self.target_cell
                cr = r1 + (r2 - r1) * ratio
                cc = c1 + (c2 - c1) * ratio
                self.current_cell = (cr, cc)
                
        elif self.state == "Jumping":
            elapsed_ms = now_ms - self.start_time_ms
            if elapsed_ms >= self.duration_ms:
                self.state = "Idle"
                self.can_be_captured_flag = True
                self.can_capture_flag = True 

    def can_be_captured(self, now_ms: int) -> bool:
        return self.can_be_captured_flag and not self._is_in_cooldown(now_ms)
        
    def can_capture(self, now_ms: int) -> bool:
        return self.can_capture_flag and not self._is_in_cooldown(now_ms)
    
    def _is_in_cooldown(self, now_ms: int) -> bool:
        if self.cooldown_start_ms == 0:
            return False
        return now_ms < (self.cooldown_start_ms + self.cooldown_duration_ms)

    def get_pos(self) -> Tuple[float, float]:
        """החזרת המיקום המדויק (לא מעוגל) לחישובי ציור"""
        if isinstance(self.current_cell, tuple) and len(self.current_cell) == 2:
            return self.current_cell
        return (0.0, 0.0)
    
    def get_cell_pos(self) -> Tuple[int, int]:
        """החזרת המיקום המעוגל לבדיקת התנגשויות"""
        r, c = self.get_pos()
        return (round(r), round(c))