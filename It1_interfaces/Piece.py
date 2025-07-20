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
        # Reset current state if needed
        if self.current_state.current_command:
            reset_cmd = Command(start_ms, self.piece_id, "Reset", [])
            self.current_state.reset(reset_cmd)

    def update(self, now_ms: int):
        self.current_state = self.current_state.update(now_ms)
        self.last_update_time = now_ms

    def draw_on_board(self, board, now_ms: int):
        sprite_img = self.current_state.graphics.get_img()
        
        # Get current position from physics
        pixel_x, pixel_y = self.current_state.physics.get_pos()
        
        # Draw the sprite
        sprite_img.draw_on(board.img, pixel_x, pixel_y)
        
        # Add cooldown overlay if piece is in cooldown
        if not self.current_state.physics.can_be_captured():
            self._draw_cooldown_overlay(board, pixel_x, pixel_y, now_ms)
    
    def _draw_cooldown_overlay(self, board: Board, x: int, y: int, now_ms: int):
        """Draw a visual overlay indicating the piece is in cooldown."""
        # Calculate cooldown progress
        cooldown_end = (self.current_state.physics.cooldown_start_ms + 
                       self.current_state.physics.cooldown_duration_ms)
        
        if now_ms < cooldown_end:
            progress = (now_ms - self.current_state.physics.cooldown_start_ms) / self.current_state.physics.cooldown_duration_ms
            
            # Create a semi-transparent overlay
            overlay_color = (0, 0, 255, 128)  # Red with transparency
            overlay_size = (board.cell_W_pix, board.cell_H_pix)
            
            # Draw cooldown indicator (simplified)
            try:
                cv2.rectangle(board.img.img, (x, y), 
                            (x + overlay_size[0], y + overlay_size[1]), 
                            overlay_color[:3], 2)
            except:
                pass  # Ignore drawing errors