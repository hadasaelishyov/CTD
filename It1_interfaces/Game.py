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

class Game:
    def __init__(self, pieces: List[Piece], board: Board):
        """Initialize the game with pieces, board, and optional event bus."""
        self.pieces = pieces
        self.board = board
        self.event_bus = EventBus() if EventBus else None
        self.user_input_queue = queue.Queue()
        self.current_board = None
        self.game_start_time = None
        self.window_name = "Chess Game"
        self.mouse_callback_active = False
        
        # מצב המשחק
        self.winner = None
        self.game_over = False
        
        # מיקומי שחקנים
        self.player1_cursor = [0, 0]
        self.player2_cursor = [0, 0]
        self.player1_selected_piece = None
        self.player2_selected_piece = None

    def game_time_ms(self) -> int:
        """Return the current game time in milliseconds."""
        if self.game_start_time is None:
            self.game_start_time = time.perf_counter()
            return 0
        return int((time.perf_counter() - self.game_start_time) * 1000)

    def clone_board(self) -> Board:
        return self.board.clone()

    def start_user_input_thread(self):
        """Start the user input thread for keyboard handling."""
        if not self.mouse_callback_active:
            cv2.namedWindow(self.window_name)
            self.mouse_callback_active = True

    def _handle_keyboard_input(self):
        """Handle keyboard input for both players."""
        key = cv2.waitKey(1) & 0xFF
        
        if key == 255:  # אין מקש
            return True
            
        # שחקן 1 (חיצים + Enter)
        if key == 82:  # חץ למעלה
            self.player1_cursor[0] = min(self.board.H_cells - 1, self.player1_cursor[0] + 1)
        elif key == 84:  # חץ למטה
            self.player1_cursor[0] = max(0, self.player1_cursor[0] - 1)
        elif key == 81:  # חץ שמאלה
            self.player1_cursor[1] = max(0, self.player1_cursor[1] - 1)
        elif key == 83:  # חץ ימינה
            self.player1_cursor[1] = min(self.board.W_cells - 1, self.player1_cursor[1] + 1)
        elif key == 13:  # Enter
            self._handle_player_action(1, self.player1_cursor)
            
        # שחקן 2 (WASD + רווח)
        elif key == ord('w'):
            self.player2_cursor[0] = min(self.board.H_cells - 1, self.player2_cursor[0] + 1)
        elif key == ord('s'):
            self.player2_cursor[0] = max(0, self.player2_cursor[0] - 1)
        elif key == ord('a'):
            self.player2_cursor[1] = max(0, self.player2_cursor[1] - 1)
        elif key == ord('d'):
            self.player2_cursor[1] = min(self.board.W_cells - 1, self.player2_cursor[1] + 1)
        elif key == ord(' '):  # רווח
            self._handle_player_action(2, self.player2_cursor)
            
        # מקשי יציאה
        elif key == ord('q') or key == 27:  # 'q' או ESC
            return False
            
        return True

    def _handle_player_action(self, player_num: int, cursor_pos: list):
        """Handle player action (select piece or move piece)."""
        row, col = cursor_pos
        piece_at_cursor = self._find_piece_at_cell(row, col)
        
        if player_num == 1:
            if self.player1_selected_piece is None:
                if piece_at_cursor and self._can_player_control_piece(1, piece_at_cursor):
                    self.player1_selected_piece = piece_at_cursor
                    print(f"Player 1 selected: {piece_at_cursor.piece_id}")
            else:
                # בדיקה אם הכלי יכול לזוז (לא בקוד השהיה)
                now_ms = self.game_time_ms()
                if self.player1_selected_piece.current_state.physics.can_capture(now_ms):
                    self._create_move_command(self.player1_selected_piece, cursor_pos)
                else:
                    print("Piece is in cooldown, cannot move!")
                self.player1_selected_piece = None
                
        elif player_num == 2:
            if self.player2_selected_piece is None:
                if piece_at_cursor and self._can_player_control_piece(2, piece_at_cursor):
                    self.player2_selected_piece = piece_at_cursor
                    print(f"Player 2 selected: {piece_at_cursor.piece_id}")
            else:
                now_ms = self.game_time_ms()
                if self.player2_selected_piece.current_state.physics.can_capture(now_ms):
                    self._create_move_command(self.player2_selected_piece, cursor_pos)
                else:
                    print("Piece is in cooldown, cannot move!")
                self.player2_selected_piece = None

    def _can_player_control_piece(self, player_num: int, piece: Piece) -> bool:
        """בדיקה אם השחקן יכול לשלוט בכלי (בהתבסס על ID או כל לוגיקה אחרת)"""
        # זה רק דוגמה - תצטרך להתאים את זה לפי המבנה שלך
        if player_num == 1:
            return "white" in piece.piece_id.lower() or "w" in piece.piece_id.lower()
        else:
            return "black" in piece.piece_id.lower() or "b" in piece.piece_id.lower()

    def _create_move_command(self, piece: Piece, target_pos: list):
        """יצירת פקודת תזוזה"""
        current_r, current_c = piece.current_state.physics.get_cell_pos()
        current_pos = chr(ord('a') + int(current_c)) + str(int(current_r) + 1)
        
        target_r, target_c = target_pos
        target_chess_pos = chr(ord('a') + target_c) + str(target_r + 1)
        
        cmd = Command(
            timestamp=self.game_time_ms(),
            piece_id=piece.piece_id,
            type="Move",
            params=[current_pos, target_chess_pos]
        )
        self.user_input_queue.put(cmd)
        print(f"Move: {piece.piece_id} from {current_pos} to {target_chess_pos}")

    def _find_piece_at_cell(self, r: int, c: int) -> Optional[Piece]:
        """מציאת כלי במיקום נתון"""
        for piece in self.pieces:
            piece_r, piece_c = piece.current_state.physics.get_cell_pos()
            if piece_r == r and piece_c == c:
                return piece
        return None

    def run(self):
        """לולאת המשחק הראשית"""
        # self.start_user_input_thread()
        start_ms = self.game_time_ms()
        
        for p in self.pieces:
            p.reset(start_ms)

        while not self._is_win():
            now = self.game_time_ms()

            # עדכון פיזיקה ואנימציות
            for p in self.pieces:
                p.update(now)

            # טיפול בקלט מקלדת
            if not self.
            ():
                break

            # טיפול בפקודות ממתינות
            while not self.user_input_queue.empty():
                cmd: Command = self.user_input_queue.get()
                self._process_input(cmd)

            # ציור
            self._draw()
            if not self._show():
                break

            # בדיקת התנגשויות
            self._resolve_collisions()

            time.sleep(0.016)  # ~60 FPS

        self._announce_win()
        cv2.destroyAllWindows()

    def _process_input(self, cmd: Command):
        """עיבוד פקודה מהמשתמש"""
        for piece in self.pieces:
            if piece.piece_id == cmd.piece_id:
                piece.on_command(cmd, self.game_time_ms())
                if self.event_bus:
                    event = Event("command_executed", {"command": cmd, "piece": piece})
                    self.event_bus.publish(event)
                break

    def _draw(self):
        """ציור המצב הנוכחי"""
        self.current_board = self.clone_board()
        now_ms = self.game_time_ms()
        
        for piece in self.pieces:
            piece.draw_on_board(self.current_board, now_ms)
        
        # ציור סמני השחקנים
        self._draw_cursor(1, self.player1_cursor, (0, 255, 0))  # ירוק לשחקן 1
        self._draw_cursor(2, self.player2_cursor, (0, 0, 255))  # אדום לשחקן 2
        
        # ציור בחירות
        if self.player1_selected_piece:
            r, c = self.player1_selected_piece.current_state.physics.get_cell_pos()
            self._draw_selection(r, c, (0, 255, 255))  # צהוב
            
        if self.player2_selected_piece:
            r, c = self.player2_selected_piece.current_state.physics.get_cell_pos()
            self._draw_selection(r, c, (255, 0, 255))  # מגנטה

    def _draw_cursor(self, player_num: int, cursor_pos: list, color: tuple):
        """ציור סמן השחקן"""
        row, col = cursor_pos
        x = col * self.board.cell_W_pix
        y = row * self.board.cell_H_pix
        
        cv2.rectangle(self.current_board.img.img, (x, y),
                     (x + self.board.cell_W_pix - 1, y + self.board.cell_H_pix - 1),
                     color, 3)
        
        self.current_board.img.put_text(str(player_num), x + 5, y + 25,
                                       0.7, (*color, 255), 2)

    def _draw_selection(self, row: int, col: int, color: tuple):
        """ציור בחירת כלי"""
        x = col * self.board.cell_W_pix
        y = row * self.board.cell_H_pix
        
        cv2.rectangle(self.current_board.img.img,
                     (x + 2, y + 2),
                     (x + self.board.cell_W_pix - 3, y + self.board.cell_H_pix - 3),
                     color, 5)

    def _show(self) -> bool:
        """הצגת הפריים הנוכחי"""
        if self.current_board is None or self.current_board.img.img is None:
            return True
            
        try:
            cv2.imshow(self.window_name, self.current_board.img.img)
            if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                return False
            return True
        except cv2.error:
            return False

    def _resolve_collisions(self):
        """פתרון התנגשויות ואכילות"""
        now_ms = self.game_time_ms()
        pieces_to_remove = []
        
        for i, piece1 in enumerate(self.pieces):
            for piece2 in self.pieces[i+1:]:
                r1, c1 = piece1.current_state.physics.get_cell_pos()
                r2, c2 = piece2.current_state.physics.get_cell_pos()
                
                # בדיקת התנגשות (אותו ריבוע)
                if r1 == r2 and c1 == c2:
                    can_p1_capture = piece1.current_state.physics.can_capture(now_ms)
                    can_p2_capture = piece2.current_state.physics.can_capture(now_ms)
                    can_p1_be_captured = piece1.current_state.physics.can_be_captured(now_ms)
                    can_p2_be_captured = piece2.current_state.physics.can_be_captured(now_ms)
                    
                    # הכלי שהתחיל לזוז ראשון אוכל את השני
                    p1_start = piece1.current_state.physics.start_time_ms or 0
                    p2_start = piece2.current_state.physics.start_time_ms or 0
                    
                    if can_p1_capture and can_p2_be_captured and p1_start < p2_start:
                        pieces_to_remove.append(piece2)
                        print(f"{piece1.piece_id} captured {piece2.piece_id}")
                    elif can_p2_capture and can_p1_be_captured and p2_start < p1_start:
                        pieces_to_remove.append(piece1)
                        print(f"{piece2.piece_id} captured {piece1.piece_id}")
        
        # הסרת הכלים שנאכלו
        for piece in pieces_to_remove:
            if piece in self.pieces:
                self.pieces.remove(piece)

    def _is_win(self) -> bool:
        """בדיקת תנאי ניצחון"""
        if self.game_over:
            return True
            
        # חיפוש מלכים
        kings = [p for p in self.pieces if "king" in p.piece_id.lower()]
        
        if len(kings) <= 1:
            self.game_over = True
            if len(kings) == 1:
                self.winner = kings[0]
            return True
            
        return False

    def _announce_win(self):
        """הכרזת המנצח"""
        if self.winner:
            print(f"Game Over! Winner: {self.winner.piece_id}")
            if self.current_board:
                self.current_board.img.put_text(f"Winner: {self.winner.piece_id}",
                                               50, 50, 2.0, (0, 255, 0, 255), 3)
                cv2.imshow(self.window_name, self.current_board.img.img)
                cv2.waitKey(3000)
        else:
            print("Game Over! Draw!")