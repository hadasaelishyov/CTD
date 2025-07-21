from typing import Tuple, Optional
from Command import Command
from Board import Board
import math


class Physics:
    SLIDE_CELLS_PER_SEC = 4.0 

    def __init__(self, start_cell: Tuple[int, int], board: Board, speed_m_s: float = 1.0):
        self.board = board
        self.speed_m_s = speed_m_s
        
        # תיקון: שמירת המיקום ההתחלתי כטופל של מספרים שלמים
        self.start_cell = tuple(start_cell)
        self.current_cell = tuple(start_cell)
        
        # משתנים לתזוזה
        self.target_cell: Optional[Tuple[int, int]] = None
        self.start_time_ms: Optional[int] = None
        self.duration_ms: Optional[int] = None
        
        # ניהול מצבים
        self.state = "Idle"
        
        # ניהול קוד השהיה
        self.cooldown_start_ms = 0
        self.cooldown_duration_ms = 0
        
        # יכולות אכילה
        self.can_be_captured_flag = True
        self.can_capture_flag = True
        
        self.current_command = None

    def copy(self):
        """יצירת עותק של האובייקט"""
        new_physics = Physics(self.start_cell, self.board, self.speed_m_s)
        new_physics.current_cell = self.current_cell
        new_physics.target_cell = self.target_cell
        new_physics.start_time_ms = self.start_time_ms
        new_physics.duration_ms = self.duration_ms
        new_physics.state = self.state
        new_physics.cooldown_start_ms = self.cooldown_start_ms
        new_physics.cooldown_duration_ms = self.cooldown_duration_ms
        new_physics.can_be_captured_flag = self.can_be_captured_flag
        new_physics.can_capture_flag = self.can_capture_flag
        new_physics.current_command = self.current_command
        return new_physics

    def reset(self, cmd: Command):
        """איפוס הפיזיקה עם פקודה חדשה - תיקון להשהיה נכונה"""
        self.current_command = cmd
        self.start_time_ms = cmd.timestamp
        
        # איפוס מצב תנועה
        self.target_cell = None
        self.duration_ms = None
        self.state = "Idle"
        
        # איפוס קוד השהיה
        self.cooldown_start_ms = 0
        self.cooldown_duration_ms = 0
        self.can_be_captured_flag = True
        self.can_capture_flag = True
        
        if cmd.type == "Move" and len(cmd.params) >= 2:
            self._handle_move_command(cmd)
        elif cmd.type == "Jump":
            self._handle_jump_command(cmd)

    def _handle_move_command(self, cmd: Command):
        """טיפול בפקודת תזוזה - תיקון להשהיה של 4 שניות"""
        start_pos = self._parse_position(cmd.params[0])
        target_pos = self._parse_position(cmd.params[1])
        
        if start_pos and target_pos:
            self.current_cell = start_pos
            self.target_cell = target_pos
            
            # חישוב משך התזוזה על בסיס המרחק
            distance = math.sqrt((target_pos[0] - start_pos[0])**2 + (target_pos[1] - start_pos[1])**2)
            self.duration_ms = int((distance / self.SLIDE_CELLS_PER_SEC) * 1000)
            
            self.state = "Moving"
            self.can_be_captured_flag = False  # במהלך תזוזה לא ניתן לאכילה
            
            # תיקון: הגדרת קוד השהיה של 4 שניות אחרי סיום התזוזה
            self.cooldown_start_ms = cmd.timestamp + self.duration_ms
            self.cooldown_duration_ms = 4000  # 4 שניות במקום 2!
            
    def _handle_jump_command(self, cmd: Command):
        """טיפול בפקודת קפיצה - תיקון להשהיה של שנייה אחת"""
        self.state = "Jumping"
        self.duration_ms = 1000  # שנייה אחת
        
        # במהלך קפיצה הכלי לא יכול לאכול או להיאכל
        self.can_be_captured_flag = False
        self.can_capture_flag = False
        
        # תיקון: קוד השהיה מתחיל אחרי סיום הקפיצה
        self.cooldown_start_ms = cmd.timestamp + self.duration_ms  # אחרי הקפיצה!
        self.cooldown_duration_ms = 1000  # שנייה אחת
    
    def _parse_position(self, pos_str: str) -> Optional[Tuple[int, int]]:
        """המרת מחרוזת מיקום (כמו 'e2') לקואורדינטות"""
        if not isinstance(pos_str, str) or len(pos_str) != 2:
            return None
        
        try:
            col = ord(pos_str[0].lower()) - ord('a')
            row = int(pos_str[1]) - 1
            
            if 0 <= col < self.board.W_cells and 0 <= row < self.board.H_cells:
                return (row, col)
        except (ValueError, IndexError):
            pass
        
        return None

    def update(self, now_ms: int):
        """עדכון מצב הפיזיקה"""
        if self.start_time_ms is None:
            return
            
        elapsed_ms = now_ms - self.start_time_ms
        
        if self.state == "Moving":
            self._update_movement(elapsed_ms)
        elif self.state == "Jumping":
            self._update_jump(elapsed_ms)

    def _update_movement(self, elapsed_ms: int):
        """עדכון תזוזה"""
        if self.duration_ms and elapsed_ms >= self.duration_ms:
            # התזוזה הסתיימה
            if self.target_cell:
                self.current_cell = self.target_cell
            self.state = "Idle"
            # שיקום יכולת האכילה רק אחרי קוד השהיה
        elif self.duration_ms and self.target_cell:
            # חישוב מיקום ביניים - תיקון חשוב!
            ratio = min(elapsed_ms / self.duration_ms, 1.0)
            
            # וודא שה-current_cell הוא tuple של מספרים שלמים לפני החישוב
            if isinstance(self.current_cell, tuple) and len(self.current_cell) == 2:
                r1, c1 = self.current_cell
            else:
                r1, c1 = self.start_cell
            
            r2, c2 = self.target_cell
            
            # חישוב מיקום רציף
            cr = r1 + (r2 - r1) * ratio
            cc = c1 + (c2 - c1) * ratio
            self.current_cell = (cr, cc)

    def _update_jump(self, elapsed_ms: int):
        """עדכון קפיצה"""
        if self.duration_ms and elapsed_ms >= self.duration_ms:
            self.state = "Idle"
            # שיקום יכולות אחרי קוד השהיה

    def can_be_captured(self, now_ms: int) -> bool:
        """בדיקה האם הכלי יכול להיאכל"""
        if not self.can_be_captured_flag:
            return False
        return not self._is_in_cooldown(now_ms)
        
    def can_capture(self, now_ms: int) -> bool:
        """בדיקה האם הכלי יכול לאכול"""
        if not self.can_capture_flag:
            return False
        return not self._is_in_cooldown(now_ms)
    
    def _is_in_cooldown(self, now_ms: int) -> bool:
        """בדיקת קוד השהיה"""
        if self.cooldown_start_ms == 0:
            return False
        return now_ms < (self.cooldown_start_ms + self.cooldown_duration_ms)

    def get_pos(self) -> Tuple[float, float]:
        """קבלת המיקום המדויק (לא מעוגל) לחישובי ציור"""
        if isinstance(self.current_cell, tuple) and len(self.current_cell) == 2:
            return (float(self.current_cell[0]), float(self.current_cell[1]))
        return (0.0, 0.0)
    
    def get_cell_pos(self) -> Tuple[int, int]:
        """קבלת המיקום המעוגל לבדיקת התנגשויות"""
        r, c = self.get_pos()
        return (round(r), round(c))
    
    def get_state(self) -> str:
        """קבלת המצב הנוכחי"""
        return self.state
    
    def is_moving(self) -> bool:
        """בדיקה האם הכלי בתנועה"""
        return self.state in ["Moving", "Jumping"]
    
    def get_progress(self, now_ms: int) -> float:
        """קבלת אחוז ההתקדמות של הפעולה הנוכחית (0.0-1.0)"""
        if self.start_time_ms is None or self.duration_ms is None:
            return 1.0
            
        elapsed_ms = now_ms - self.start_time_ms
        return min(elapsed_ms / self.duration_ms, 1.0)
    
    def get_cooldown_progress(self, now_ms: int) -> float:
        """קבלת אחוז ההתקדמות של קוד השהיה (0.0-1.0)"""
        if not self._is_in_cooldown(now_ms):
            return 1.0
            
        elapsed = now_ms - self.cooldown_start_ms
        return min(elapsed / self.cooldown_duration_ms, 1.0)
    
    def set_position(self, cell: Tuple[int, int]):
        """הגדרת מיקום ישירות (למשחק חדש או טלפורט)"""
        self.current_cell = tuple(cell)
        self.start_cell = tuple(cell)
        self.target_cell = None
        self.state = "Idle"
    
    def stop_movement(self):
        """עצירת תנועה מיידית"""
        if self.state in ["Moving", "Jumping"]:
            self.state = "Idle"
            self.target_cell = None
            self.duration_ms = None
            # החזרת יכולות לרגיל
            self.can_be_captured_flag = True
            self.can_capture_flag = True
    def can_pass_through(self, now_ms: int) -> bool:
        """בדיקה האם כלי יכול לעבור דרך (במהלך קפיצה)"""
        return self.state == "Jumping"

    def is_in_air(self, now_ms: int) -> bool:
        """בדיקה האם הכלי באוויר (קופץ)"""
        return self.state == "Jumping"

    def get_movement_start_time(self) -> int:
        """קבלת זמן תחילת התנועה - לצורך קביעת עדיפות בהתנגשות"""
        return self.start_time_ms if self.start_time_ms else 0