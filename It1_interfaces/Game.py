import inspect
import pathlib
import queue, threading, time, cv2, math
from typing import List, Dict, Tuple, Optional
from Board   import Board
from Bus.bus import EventBus, Event
from Command import Command
from Piece   import Piece
from img     import Img


class InvalidBoard(Exception): ...

# ────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self, pieces: List[Piece], board: Board):
        """Initialize the game with pieces, board, and optional event bus."""
        self.pieces = pieces
        self.board = board
        self.event_bus = EventBus() if EventBus else None
        self.user_input_queue = queue.Queue()
        self.current_board = None
        self.game_start_time = None
        self.window_name = "Game Board"
        self.mouse_callback_active = False
        
        # Game state
        self.winner = None
        self.game_over = False

    # ─── helpers ─────────────────────────────────────────────────────────────
    def game_time_ms(self) -> int:
        """Return the current game time in milliseconds."""
        if self.game_start_time is None:
            self.game_start_time = time.perf_counter()
        return int(time.perf_counter() - self.game_start_time)

    def clone_board(self) -> Board:
        """
        Return a **brand-new** Board wrapping a copy of the background pixels
        so we can paint sprites without touching the pristine board.
        """
        return self.board.clone()

    def start_user_input_thread(self):
        """Start the user input thread for keyboard handling."""
        if not self.mouse_callback_active:
            cv2.namedWindow(self.window_name)
            self.mouse_callback_active = True
            
        # Initialize player cursors and selection
        self.player1_cursor = [0, 0]  # [row, col]
        self.player2_cursor = [0, 0]  # [row, col]
        self.player1_selected_piece = None
        self.player2_selected_piece = None

    def _handle_keyboard_input(self):
        """Handle keyboard input for both players."""
        key = cv2.waitKey(1) & 0xFF
        
        if key == 255:  # No key pressed
            return True
            
        # Player 1 controls (Arrow keys + Enter)
        if key == 82:  # Up arrow
            self.player1_cursor[0] = max(0, self.player1_cursor[0] - 1)
        elif key == 84:  # Down arrow
            self.player1_cursor[0] = min(self.board.H_cells - 1, self.player1_cursor[0] + 1)
        elif key == 81:  # Left arrow
            self.player1_cursor[1] = max(0, self.player1_cursor[1] - 1)
        elif key == 83:  # Right arrow
            self.player1_cursor[1] = min(self.board.W_cells - 1, self.player1_cursor[1] + 1)
        elif key == 13:  # Enter
            self._handle_player_action(1, self.player1_cursor)
            
        # Player 2 controls (WASD + Space)
        elif key == ord('w'):
            self.player2_cursor[0] = max(0, self.player2_cursor[0] - 1)
        elif key == ord('s'):
            self.player2_cursor[0] = min(self.board.H_cells - 1, self.player2_cursor[0] + 1)
        elif key == ord('a'):
            self.player2_cursor[1] = max(0, self.player2_cursor[1] - 1)
        elif key == ord('d'):
            self.player2_cursor[1] = min(self.board.W_cells - 1, self.player2_cursor[1] + 1)
        elif key == ord(' '):  # Space
            self._handle_player_action(2, self.player2_cursor)
            
        # Exit keys
        elif key == ord('q') or key == 27:  # 'q' or ESC
            return False
            
        return True

    def _handle_player_action(self, player_num: int, cursor_pos: list):
        """Handle player action (select piece or move piece)."""
        row, col = cursor_pos
        piece_at_cursor = self._find_piece_at_cell(row, col)
        
        if player_num == 1:
            if self.player1_selected_piece is None:
                # Select piece
                if piece_at_cursor:
                    self.player1_selected_piece = piece_at_cursor
                    print(f"Player 1 selected piece: {piece_at_cursor.piece_id}")
            else:
                # Move piece
                self._create_move_command(self.player1_selected_piece, cursor_pos)
                self.player1_selected_piece = None
                
        elif player_num == 2:
            if self.player2_selected_piece is None:
                # Select piece
                if piece_at_cursor:
                    self.player2_selected_piece = piece_at_cursor
                    print(f"Player 2 selected piece: {piece_at_cursor.piece_id}")
            else:
                # Move piece
                self._create_move_command(self.player2_selected_piece, cursor_pos)
                self.player2_selected_piece = None

    def _create_move_command(self, piece: Piece, target_pos: list):
        """Create and queue a move command."""
        # Get current piece position
        current_r, current_c = piece.current_state.physics.get_pos()
        current_pos = chr(ord('a') + int(current_c)) + str(int(current_r) + 1)
        
        # Create target position
        target_r, target_c = target_pos
        target_chess_pos = chr(ord('a') + target_c) + str(target_r + 1)
        
        cmd = Command(
            timestamp=self.game_time_ms(),
            piece_id=piece.piece_id,
            type="Move",
            params=[current_pos, target_chess_pos]
        )
        self.user_input_queue.put(cmd)
        print(f"Move command: {piece.piece_id} from {current_pos} to {target_chess_pos}")

    def _find_piece_at_cell(self, r: int, c: int) -> Optional[Piece]:
        """Find piece at the given cell coordinates."""
        for piece in self.pieces:
            piece_r, piece_c = piece.current_state.physics.get_pos()
            if abs(piece_r - r) < 0.5 and abs(piece_c - c) < 0.5:
                return piece
        return None

    # ─── main public entrypoint ──────────────────────────────────────────────
    def run(self):
        """Main game loop."""
        self.start_user_input_thread()

        start_ms = self.game_time_ms()
        for p in self.pieces:
            p.reset(start_ms)

        # ─────── main loop ──────────────────────────────────────────────────
        while not self._is_win():
            now = self.game_time_ms()

            # (1) update physics & animations
            for p in self.pieces:
                p.update(now)

            # (2) handle keyboard input
            if not self._handle_keyboard_input():
                break

            # (3) handle queued Commands from keyboard input
            while not self.user_input_queue.empty():
                cmd: Command = self.user_input_queue.get()
                self._process_input(cmd)

            # (4) draw current position
            self._draw()
            if not self._show():           # returns False if user closed window
                break

            # (5) detect captures
            self._resolve_collisions()

            # Small delay to control frame rate
            time.sleep(0.016)  # ~60 FPS

        self._announce_win()
        cv2.destroyAllWindows()

    def _process_input(self, cmd: Command):
        """Process a user input command."""
        # Find the piece that should execute this command
        target_piece = None
        for piece in self.pieces:
            if piece.piece_id == cmd.piece_id:
                target_piece = piece
                break
        
        if target_piece:
            target_piece.on_command(cmd, self.game_time_ms())
            
            # Publish event if event bus is available
            if self.event_bus:
                event = Event("command_executed", {"command": cmd, "piece": target_piece})
                self.event_bus.publish(event)

    # ─── drawing helpers ────────────────────────────────────────────────────
    def _draw(self):
        """Draw the current game state."""
        # Start with a fresh copy of the board
        self.current_board = self.clone_board()
        
        # Draw all pieces on the board
        now_ms = self.game_time_ms()
        for piece in self.pieces:
            try:
                piece.draw_on_board(self.current_board, now_ms)
            except Exception as e:
                print(f"Error drawing piece {piece.piece_id}: {e}")
                continue
        
        # Draw player cursors
        self._draw_cursor(1, self.player1_cursor, (0, 255, 0))  # Green for player 1
        self._draw_cursor(2, self.player2_cursor, (0, 0, 255))  # Red for player 2
        
        # Draw selection indicators
        if self.player1_selected_piece:
            r, c = self.player1_selected_piece.current_state.physics.get_pos()
            self._draw_selection(int(r), int(c), (0, 255, 255))  # Yellow for player 1 selection
            
        if self.player2_selected_piece:
            r, c = self.player2_selected_piece.current_state.physics.get_pos()
            self._draw_selection(int(r), int(c), (255, 0, 255))  # Magenta for player 2 selection

    def _draw_cursor(self, player_num: int, cursor_pos: list, color: tuple):
        """Draw player cursor on the board."""
        row, col = cursor_pos
        x = col * self.board.cell_W_pix
        y = row * self.board.cell_H_pix
        
        # Draw cursor border
        cv2.rectangle(
            self.current_board.img.img,
            (x, y),
            (x + self.board.cell_W_pix - 1, y + self.board.cell_H_pix - 1),
            color,
            3
        )
        
        # Draw player number
        self.current_board.img.put_text(
            str(player_num),
            x + 5, y + 25,
            font_size=0.7,
            color=(*color, 255),
            thickness=2
        )

    def _draw_selection(self, row: int, col: int, color: tuple):
        """Draw selection indicator for selected piece."""
        x = col * self.board.cell_W_pix
        y = row * self.board.cell_H_pix
        
        # Draw selection border (thicker than cursor)
        cv2.rectangle(
            self.current_board.img.img,
            (x + 2, y + 2),
            (x + self.board.cell_W_pix - 3, y + self.board.cell_H_pix - 3),
            color,
            5
        )

    def _show(self) -> bool:
        """Show the current frame and handle window events."""
        if self.current_board is None or self.current_board.img.img is None:
            return True
            
        try:
            cv2.imshow(self.window_name, self.current_board.img.img)
            
            # Check if window was closed
            if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                return False
                
            return True
        except cv2.error:
            return False

    # ─── capture resolution ────────────────────────────────────────────────
    def _resolve_collisions(self):
        """Resolve piece collisions and captures."""
        now_ms = self.game_time_ms()
        pieces_to_remove = []
        
        for i, piece1 in enumerate(self.pieces):
            for j, piece2 in enumerate(self.pieces[i+1:], i+1):
                # Get current positions
                r1, c1 = piece1.current_state.physics.get_pos()
                r2, c2 = piece2.current_state.physics.get_pos()
                
                # Check if pieces are in the same cell (collision)
                distance = math.sqrt((r1 - r2)**2 + (c1 - c2)**2)
                
                if distance < 0.8:  # Close enough to be considered same cell
                    # Determine capture based on physics states
                    can_piece1_capture = piece1.current_state.physics.can_capture(now_ms)
                    can_piece2_capture = piece2.current_state.physics.can_capture(now_ms)
                    can_piece1_be_captured = piece1.current_state.physics.can_be_captured(now_ms)
                    can_piece2_be_captured = piece2.current_state.physics.can_be_captured(now_ms)
                    
                    # Capture logic
                    if can_piece1_capture and can_piece2_be_captured:
                        pieces_to_remove.append(piece2)
                        print(f"Piece {piece1.piece_id} captured {piece2.piece_id}")
                    elif can_piece2_capture and can_piece1_be_captured:
                        pieces_to_remove.append(piece1)
                        print(f"Piece {piece2.piece_id} captured {piece1.piece_id}")
        
        # Remove captured pieces
        for piece in pieces_to_remove:
            if piece in self.pieces:
                self.pieces.remove(piece)

    # ─── board validation & win detection ───────────────────────────────────
    def _is_win(self) -> bool:
        """Check if the game has ended."""
        if self.game_over:
            return True
            
        # Simple win condition: only one piece remaining
        if len(self.pieces) <= 1:
            self.game_over = True
            if len(self.pieces) == 1:
                self.winner = self.pieces[0]
            return True
            
        return False

    def _announce_win(self):
        """Announce the winner."""
        if self.winner:
            print(f"Game Over! Winner: {self.winner.piece_id}")
            
            # Draw winner message on board
            if self.current_board:
                self.current_board.img.put_text(
                    f"Winner: {self.winner.piece_id}",
                    50, 50,
                    font_size=2.0,
                    color=(0, 255, 0, 255),  # Green
                    thickness=3
                )
                cv2.imshow(self.window_name, self.current_board.img.img)
                cv2.waitKey(3000)  # Show for 3 seconds
        else:
            print("Game Over! No winner.")