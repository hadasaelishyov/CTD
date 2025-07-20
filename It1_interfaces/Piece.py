from Board import Board
from Command import Command
from State import State
import cv2

class Piece:
    def __init__(self, piece_id: str, init_state: State):
        """Initialize a piece with ID and initial state."""
        self.piece_id = piece_id
        self.current_state = init_state
        self.last_update_time = 0

    def on_command(self, cmd: Command, now_ms: int):
        if cmd.piece_id == self.piece_id:
            self.current_state = self.current_state.get_state_after_command(cmd, now_ms)

    def reset(self, start_ms: int):
        self.last_update_time = start_ms
        if self.current_state.current_command:
            reset_cmd = Command(start_ms, self.piece_id, "Reset", [])
            self.current_state.reset(reset_cmd)

    def update(self, now_ms: int):
        self.current_state = self.current_state.update(now_ms)
        self.last_update_time = now_ms

    def draw_on_board(self, board: Board, now_ms: int):
        sprite_img = self.current_state.graphics.get_img()
        
        # קבלת המיקום המדויק מהפיזיקה
        cell_r, cell_c = self.current_state.physics.get_pos()
        
        # המרה לפיקסלים
        pixel_x = int(cell_c * board.cell_W_pix)
        pixel_y = int(cell_r * board.cell_H_pix)
        
        # ציור הספרייט
        try:
            sprite_img.draw_on(board.img, pixel_x, pixel_y)
        except Exception as e:
            print(f"Error drawing piece {self.piece_id}: {e}")
        
        # הוספת אינדיקטור קוד השהיה
        if not self.current_state.physics.can_be_captured(now_ms):
            self._draw_cooldown_overlay(board, pixel_x, pixel_y, now_ms)
    
    def _draw_cooldown_overlay(self, board: Board, x: int, y: int, now_ms: int):
        """ציור אינדיקטור קוד השהיה"""
        cooldown_end = (self.current_state.physics.cooldown_start_ms + 
                       self.current_state.physics.cooldown_duration_ms)
        
        if now_ms < cooldown_end:
            # ציור מסגרת אדומה לציון קוד השהיה
            try:
                cv2.rectangle(board.img.img, 
                            (x, y), 
                            (x + board.cell_W_pix - 1, y + board.cell_H_pix - 1), 
                            (0, 0, 255), 3)  # מסגרת אדומה
            except:
                pass
