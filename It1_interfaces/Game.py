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
        self.event_bus = EventBus()
        self.user_input_queue = queue.Queue()
        self.current_board = None
        self.game_start_time = None
        self.window_name = "Chess Game"
        self.mouse_callback_active = False
        
        # מצב המשחק
        self.winner = None
        self.game_over = False
        self.current_turn = "white"  # "white" or "black"
        
        # מיקומי שחקנים
        self.player1_cursor = [0, 0]  # [row, col]
        self.player2_cursor = [7, 7]  # [row, col]
        self.player1_selected_piece = None
        self.player2_selected_piece = None
        
        # מיפוי שחקנים לצבעים
        self.player_colors = {1: "white", 2: "black"}
        
        # FPS control
        self.target_fps = 30
        self.frame_time = 1.0 / self.target_fps
        self.last_frame_time = time.perf_counter()
        
        # הגדרת event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """הגדרת מאזינים לאירועים"""
        self.event_bus.subscribe("piece_moved", self._on_piece_moved)
        self.event_bus.subscribe("piece_captured", self._on_piece_captured)
        self.event_bus.subscribe("turn_changed", self._on_turn_changed)

    def _on_piece_moved(self, event: Event):
        """טיפול באירוע תזוזת כלי"""
        print(f"Piece moved: {event.data['piece_id']} to {event.data['position']}")

    def _on_piece_captured(self, event: Event):
        """טיפול באירוע אכילת כלי"""
        print(f"Piece captured: {event.data['captured_piece']} by {event.data['capturing_piece']}")

    def _on_turn_changed(self, event: Event):
        """טיפול באירוע החלפת תור"""
        print(f"Turn changed to: {event.data['new_turn']}")

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
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
            self.mouse_callback_active = True

    def _handle_keyboard_input(self):
        """Handle keyboard input for both players."""
        key = cv2.waitKey(1) & 0xFF
        
        if key == 255:  # אין מקש
            return True
        
        # בדיקה איזה שחקן בתור
        current_player = 1 if self.current_turn == "white" else 2
        
        # שחקן 1 (חיצים + Enter) - רק כשזה התור שלו
        if current_player == 1:
            if key == 82 or key == ord('w'):  # חץ למעלה או W
                self.player1_cursor[0] = max(0, self.player1_cursor[0] - 1)
            elif key == 84 or key == ord('s'):  # חץ למטה או S
                self.player1_cursor[0] = min(self.board.H_cells - 1, self.player1_cursor[0] + 1)
            elif key == 81 or key == ord('a'):  # חץ שמאלה או A
                self.player1_cursor[1] = max(0, self.player1_cursor[1] - 1)
            elif key == 83 or key == ord('d'):  # חץ ימינה או D
                self.player1_cursor[1] = min(self.board.W_cells - 1, self.player1_cursor[1] + 1)
            elif key == 13 or key == ord(' '):  # Enter או רווח
                self._handle_player_action(1, self.player1_cursor)
            
        # שחקן 2 (WASD + רווח) - רק כשזה התור שלו
        elif current_player == 2:
            if key == ord('i'):  # I במקום W
                self.player2_cursor[0] = max(0, self.player2_cursor[0] - 1)
            elif key == ord('k'):  # K במקום S
                self.player2_cursor[0] = min(self.board.H_cells - 1, self.player2_cursor[0] + 1)
            elif key == ord('j'):  # J במקום A
                self.player2_cursor[1] = max(0, self.player2_cursor[1] - 1)
            elif key == ord('l'):  # L במקום D
                self.player2_cursor[1] = min(self.board.W_cells - 1, self.player2_cursor[1] + 1)
            elif key == ord('u'):  # U לבחירה
                self._handle_player_action(2, self.player2_cursor)
        
        # מקשי יציאה - תמיד פעילים
        if key == ord('q') or key == 27:  # 'q' או ESC
            return False
        
        # מקש לאיפוס בחירה
        if key == ord('r'):
            self.player1_selected_piece = None
            self.player2_selected_piece = None
            print("Selection reset")
            
        return True

    def _handle_player_action(self, player_num: int, cursor_pos: list):
        """Handle player action (select piece or move piece)."""
        row, col = cursor_pos
        piece_at_cursor = self._find_piece_at_cell(row, col)
        
        # בדיקה שזה התור של השחקן
        if self.player_colors[player_num] != self.current_turn:
            print(f"Not your turn! Current turn: {self.current_turn}")
            return
        
        if player_num == 1:
            if self.player1_selected_piece is None:
                # בחירת כלי
                if piece_at_cursor and self._can_player_control_piece(1, piece_at_cursor):
                    self.player1_selected_piece = piece_at_cursor
                    print(f"Player 1 selected: {piece_at_cursor.piece_id}")
                else:
                    print("No valid piece to select at this position")
            else:
                # ניסיון להזיז כלי
                if self._attempt_move(self.player1_selected_piece, cursor_pos):
                    self.player1_selected_piece = None
                    self._change_turn()
                else:
                    # אם המהלך לא חוקי, בדוק אם רוצים לבחור כלי אחר
                    if piece_at_cursor and self._can_player_control_piece(1, piece_at_cursor):
                        self.player1_selected_piece = piece_at_cursor
                        print(f"Player 1 selected: {piece_at_cursor.piece_id}")
                    else:
                        print("Invalid move!")
                        self.player1_selected_piece = None
                
        elif player_num == 2:
            if self.player2_selected_piece is None:
                # בחירת כלי
                if piece_at_cursor and self._can_player_control_piece(2, piece_at_cursor):
                    self.player2_selected_piece = piece_at_cursor
                    print(f"Player 2 selected: {piece_at_cursor.piece_id}")
                else:
                    print("No valid piece to select at this position")
            else:
                # ניסיון להזיז כלי
                if self._attempt_move(self.player2_selected_piece, cursor_pos):
                    self.player2_selected_piece = None
                    self._change_turn()
                else:
                    # אם המהלך לא חוקי, בדוק אם רוצים לבחור כלי אחר
                    if piece_at_cursor and self._can_player_control_piece(2, piece_at_cursor):
                        self.player2_selected_piece = piece_at_cursor
                        print(f"Player 2 selected: {piece_at_cursor.piece_id}")
                    else:
                        print("Invalid move!")
                        self.player2_selected_piece = None

    def _attempt_move(self, piece: Piece, target_pos: list) -> bool:
        """ניסיון להזיז כלי - מחזיר True אם המהלך בוצע בהצלחה"""
        now_ms = self.game_time_ms()
        
        # בדיקה בסיסית של הכלי
        if not hasattr(piece, 'current_state') or not piece.current_state:
            print("Piece has no current state!")
            return False
            
        if not hasattr(piece.current_state, 'physics') or not piece.current_state.physics:
            print("Piece has no physics state!")
            return False
        
        # בדיקה אם הכלי בקירור (אם יש פונקציה כזאת)
        if hasattr(piece.current_state.physics, 'can_capture'):
            try:
                if not piece.current_state.physics.can_capture(now_ms):
                    print("Piece is in cooldown, cannot move!")
                    return False
            except:
                pass  # אם הפונקציה לא עובדת, נמשיך
        
        target_row, target_col = target_pos
        
        try:
            current_row, current_col = piece.current_state.physics.get_cell_pos()
        except Exception as e:
            print(f"Error getting piece position: {e}")
            return False
        
        # בדיקה בסיסית של תזוזה
        if current_row == target_row and current_col == target_col:
            print("Cannot move to same position!")
            return False
        
        # בדיקה אם התזוזה בגבולות הלוח
        if not (0 <= target_row < self.board.H_cells and 0 <= target_col < self.board.W_cells):
            print("Move is out of board bounds!")
            return False
        
        # בדיקה אם יש כלי יריב במיקום היעד
        target_piece = self._find_piece_at_cell(target_row, target_col)
        if target_piece:
            if self._is_same_team(piece, target_piece):
                print("Cannot capture your own piece!")
                return False
            else:
                print(f"{piece.piece_id} will capture {target_piece.piece_id}")
        
        # יצירת פקודת תזוזה
        self._create_move_command(piece, target_pos)
        return True

    def _change_turn(self):
        """החלפת תור"""
        self.current_turn = "black" if self.current_turn == "white" else "white"
        
        # פרסום אירוע החלפת תור
        event = Event("turn_changed", {"new_turn": self.current_turn})
        self.event_bus.publish(event)

    def _can_player_control_piece(self, player_num: int, piece: Piece) -> bool:
        """בדיקה אם השחקן יכול לשלוט בכלי"""
        piece_id_lower = piece.piece_id.lower()
        
        if player_num == 1:  # שחקן לבן
            return any(identifier in piece_id_lower for identifier in ["white", "w_", "_w", "light", "bw", "kw", "nw", "pw", "qw", "rw"])
        else:  # שחקן שחור
            return any(identifier in piece_id_lower for identifier in ["black", "b_", "_b", "dark", "bb", "kb", "nb", "pb", "qb", "rb"])
    
    def _is_same_team(self, piece1: Piece, piece2: Piece) -> bool:
        """בדיקה אם שני כלים שייכים לאותה קבוצה"""
        p1_id = piece1.piece_id.lower()
        p2_id = piece2.piece_id.lower()
        
        # בדיקה אם שניהם לבנים
        p1_white = any(identifier in p1_id for identifier in ["white", "w_", "_w", "light", "bw", "kw", "nw", "pw", "qw", "rw"])
        p2_white = any(identifier in p2_id for identifier in ["white", "w_", "_w", "light", "bw", "kw", "nw", "pw", "qw", "rw"])
        
        # בדיקה אם שניהם שחורים
        p1_black = any(identifier in p1_id for identifier in ["black", "b_", "_b", "dark", "bb", "kb", "nb", "pb", "qb", "rb"])
        p2_black = any (identifier in p2_id for identifier in ["black", "b_", "_b", "dark", "bb", "kb", "nb", "pb", "qb", "rb"])
        
        return (p1_white and p2_white) or (p1_black and p2_black)

    def _create_move_command(self, piece: Piece, target_pos: list):
        """יצירת פקודת תזוזה"""
        try:
            current_r, current_c = piece.current_state.physics.get_cell_pos()
            
            target_r, target_c = target_pos
            
            # עדכון ישיר של מיקום הכלי (לדמו)
            piece.current_state.physics.row = target_r
            piece.current_state.physics.col = target_c
            
            # המרה לסימון שח
            current_pos = chr(ord('a') + int(current_c)) + str(int(current_r) + 1)
            target_chess_pos = chr(ord('a') + target_c) + str(target_r + 1)
            
            cmd = Command(
                timestamp=self.game_time_ms(),
                piece_id=piece.piece_id,
                type="Move",
                params=[current_pos, target_chess_pos]
            )
            
            self.user_input_queue.put(cmd)
            print(f"Move command created: {piece.piece_id} from {current_pos} to {target_chess_pos}")
        except Exception as e:
            print(f"Error creating move command: {e}")

    def _find_piece_at_cell(self, r: int, c: int) -> Optional[Piece]:
        """מציאת כלי במיקום נתון"""
        for piece in self.pieces:
            try:
                if hasattr(piece, 'current_state') and piece.current_state and \
                   hasattr(piece.current_state, 'physics') and piece.current_state.physics:
                    piece_r, piece_c = piece.current_state.physics.get_cell_pos()
                    if piece_r == r and piece_c == c:
                        return piece
            except Exception as e:
                print(f"Error checking piece position: {e}")
                continue
        return None

    def run(self):
        """לולאת המשחק הראשית"""
        self.start_user_input_thread()
        start_ms = self.game_time_ms()
        
        # איפוס כל הכלים
        for p in self.pieces:
            try:
                if hasattr(p, 'reset'):
                    p.reset(start_ms)
            except Exception as e:
                print(f"Error resetting piece {p.piece_id}: {e}")

        print(f"Game started! Current turn: {self.current_turn}")
        print("White player (Player 1): Arrow keys (or WASD) + Enter/Space")
        print("Black player (Player 2): IJKL + U")
        print("Press 'r' to reset selection, 'q' to quit")

        frame_count = 0
        while not self._is_win():
            current_time = time.perf_counter()
            now = self.game_time_ms()
            frame_count += 1

            # עדכון פיזיקה ואנימציות
            for p in self.pieces:
                try:
                    if hasattr(p, 'update'):
                        p.update(now)
                except Exception as e:
                    if frame_count % 300 == 0:  # הדפס רק כל 10 שניות בערך
                        print(f"Error updating piece {p.piece_id}: {e}")

            # טיפול בקלט מקלדת
            try:
                if not self._handle_keyboard_input():
                    break
            except Exception as e:
                print(f"Error handling keyboard input: {e}")

            # טיפול בפקודות ממתינות
            try:
                while not self.user_input_queue.empty():
                    cmd: Command = self.user_input_queue.get()
                    self._process_input(cmd)
            except Exception as e:
                print(f"Error processing input: {e}")

            # ציור
            try:
                self._draw()
                if not self._show():
                    break
            except Exception as e:
                print(f"Error drawing/showing frame: {e}")

            # בדיקת התנגשויות
            try:
                self._resolve_collisions()
            except Exception as e:
                print(f"Error resolving collisions: {e}")

            # FPS control
            elapsed = time.perf_counter() - current_time
            if elapsed < self.frame_time:
                time.sleep(self.frame_time - elapsed)

        self._announce_win()
        cv2.destroyAllWindows()

    def _process_input(self, cmd: Command):
        """עיבוד פקודה מהמשתמש"""
        for piece in self.pieces:
            if piece.piece_id == cmd.piece_id:
                try:
                    if hasattr(piece, 'on_command'):
                        piece.on_command(cmd, self.game_time_ms())
                    
                    # פרסום אירוע תזוזה
                    if cmd.type == "Move":
                        event = Event("piece_moved", {
                            "piece_id": piece.piece_id,
                            "command": cmd,
                            "position": cmd.params[1] if len(cmd.params) > 1 else None
                        })
                        self.event_bus.publish(event)
                except Exception as e:
                    print(f"Error processing command for piece {piece.piece_id}: {e}")
                break

    def _draw(self):
        """ציור המצב הנוכחי"""
        try:
            self.current_board = self.clone_board()
            now_ms = self.game_time_ms()
            
            # ציור כל הכלים
            for piece in self.pieces:
                try:
                    if hasattr(piece, 'draw_on_board'):
                        piece.draw_on_board(self.current_board, now_ms)
                    else:
                        # ציור פשוט לדמו
                        self._draw_demo_piece(piece)
                except Exception as e:
                    print(f"Error drawing piece {piece.piece_id}: {e}")
            
            # ציור סמני השחקנים - רק של השחקן שבתור
            if self.current_turn == "white":
                self._draw_cursor(1, self.player1_cursor, (0, 255, 0))  # ירוק לשחקן 1
            else:
                self._draw_cursor(2, self.player2_cursor, (0, 0, 255))  # אדום לשחקן 2
            
            # ציור בחירות
            if self.player1_selected_piece and self.current_turn == "white":
                try:
                    r, c = self.player1_selected_piece.current_state.physics.get_cell_pos()
                    self._draw_selection(r, c, (0, 255, 255))  # צהוב
                except Exception as e:
                    print(f"Error drawing player 1 selection: {e}")
                    
            if self.player2_selected_piece and self.current_turn == "black":
                try:
                    r, c = self.player2_selected_piece.current_state.physics.get_cell_pos()
                    self._draw_selection(r, c, (255, 0, 255))  # מגנטה
                except Exception as e:
                    print(f"Error drawing player 2 selection: {e}")
            
            # הצגת מידע על המשחק
            self._draw_game_info()
            
        except Exception as e:
            print(f"Error in draw method: {e}")

    def _draw_demo_piece(self, piece: Piece):
        """ציור משופר לכלי דמו"""
        try:
            r, c = piece.current_state.physics.get_cell_pos()
            x = c * self.current_board.cell_W_pix + 10
            y = r * self.current_board.cell_H_pix + 10
            
            # צבע לפי השחקן
            if self._can_player_control_piece(1, piece):
                color = (255, 255, 255)  # לבן
                border_color = (200, 200, 200)
            else:
                color = (50, 50, 50)  # כמעט שחור
                border_color = (100, 100, 100)
            
            # ציור ריבוע עם צללית
            shadow_offset = 3
            cv2.rectangle(self.current_board.img.img, 
                        (x + shadow_offset, y + shadow_offset), 
                        (x + 60 + shadow_offset, y + 60 + shadow_offset), 
                        (0, 0, 0), -1)
            
            # ציור הכלי עצמו
            cv2.rectangle(self.current_board.img.img, 
                        (x, y), 
                        (x + 60, y + 60), 
                        color, -1)
            cv2.rectangle(self.current_board.img.img, 
                        (x, y), 
                        (x + 60, y + 60), 
                        border_color, 2)
                        
            # הוספת טקסט משופר
            piece_name = piece.piece_id
            if "_" in piece_name:
                # נקח את החלק האחרון של השם
                piece_type = piece_name.split('_')[0][:2].upper()
            else:
                piece_type = piece_name[:2].upper()
            
            # בחירת צבע טקסט
            text_color = (0, 0, 0) if self._can_player_control_piece(1, piece) else (255, 255, 255)
            
            cv2.putText(self.current_board.img.img, piece_type, 
                    (x + 15, y + 35), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, text_color, 2)
                    
        except Exception as e:
            print(f"Error drawing demo piece: {e}")

    def _draw_cursor(self, player_num: int, cursor_pos: list, color: tuple):
        """ציור סמן השחקן"""
        try:
            row, col = cursor_pos
            x = col * self.board.cell_W_pix
            y = row * self.board.cell_H_pix
            
            # ציור מסגרת סמן
            cv2.rectangle(self.current_board.img.img, (x, y),
                         (x + self.board.cell_W_pix - 1, y + self.board.cell_H_pix - 1),
                         color, 3)
            
            # הצגת מספר השחקן
            if hasattr(self.current_board.img, 'put_text'):
                self.current_board.img.put_text(str(player_num), x + 5, y + 25,
                                               0.7, (*color, 255), 2)
            else:
                cv2.putText(self.current_board.img.img, str(player_num), 
                           (x + 5, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, color, 2)
        except Exception as e:
            print(f"Error drawing cursor: {e}")

    def _draw_selection(self, row: int, col: int, color: tuple):
        """ציור בחירת כלי"""
        try:
            x = col * self.board.cell_W_pix
            y = row * self.board.cell_H_pix
            
            # מסגרת עבה לציון בחירה
            cv2.rectangle(self.current_board.img.img,
                         (x + 2, y + 2),
                         (x + self.board.cell_W_pix - 3, y + self.board.cell_H_pix - 3),
                         color, 5)
        except Exception as e:
            print(f"Error drawing selection: {e}")

    def _draw_game_info(self):
        """ציור מידע משופר על המשחק - להחליף בקלאס Game"""
        try:
            # מידע על התור הנוכחי עם רקע
            turn_text = f"Turn: {self.current_turn.capitalize()}"
            
            # ציור רקע לטקסט
            cv2.rectangle(self.current_board.img.img, (5, 5), (200, 40), (0, 0, 0), -1)
            cv2.rectangle(self.current_board.img.img, (5, 5), (200, 40), (255, 255, 255), 2)
            
            if hasattr(self.current_board.img, 'put_text'):
                self.current_board.img.put_text(turn_text, 10, 30, 1.0, (255, 255, 255, 255), 2)
            else:
                cv2.putText(self.current_board.img.img, turn_text, 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                        1.0, (255, 255, 255), 2)
            
            # מידע על הכלי הנבחר
            selected_piece = None
            if self.current_turn == "white" and self.player1_selected_piece:
                selected_piece = self.player1_selected_piece
            elif self.current_turn == "black" and self.player2_selected_piece:
                selected_piece = self.player2_selected_piece
                
            if selected_piece:
                selected_text = f"Selected: {selected_piece.piece_id}"
                
                # ציור רקע לטקסט הבחירה
                cv2.rectangle(self.current_board.img.img, (5, 45), (300, 80), (0, 50, 0), -1)
                cv2.rectangle(self.current_board.img.img, (5, 45), (300, 80), (0, 255, 0), 2)
                
                if hasattr(self.current_board.img, 'put_text'):
                    self.current_board.img.put_text(selected_text, 10, 70, 0.8, (255, 255, 0, 255), 2)
                else:
                    cv2.putText(self.current_board.img.img, selected_text, 
                            (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                            0.8, (255, 255, 0), 2)
            
            # הצגת מספר הכלים שנותרו
            white_pieces = [p for p in self.pieces if self._can_player_control_piece(1, p)]
            black_pieces = [p for p in self.pieces if self._can_player_control_piece(2, p)]
            
            pieces_info = f"White: {len(white_pieces)} | Black: {len(black_pieces)}"
            
            if hasattr(self.current_board.img, 'put_text'):
                self.current_board.img.put_text(pieces_info, 10, 100, 0.6, (200, 200, 200, 255), 1)
            else:
                cv2.putText(self.current_board.img.img, pieces_info, 
                        (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.6, (200, 200, 200), 1)
        except Exception as e:
            print(f"Error drawing game info: {e}")

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
        except Exception as e:
            print(f"Error showing frame: {e}")
            return False

    def _resolve_collisions(self):
        """פתרון התנגשויות ואכילות"""
        try:
            now_ms = self.game_time_ms()
            pieces_to_remove = []
            
            for i, piece1 in enumerate(self.pieces):
                if not hasattr(piece1, 'current_state') or not piece1.current_state:
                    continue
                    
                for piece2 in self.pieces[i+1:]:
                    if not hasattr(piece2, 'current_state') or not piece2.current_state:
                        continue
                        
                    try:
                        r1, c1 = piece1.current_state.physics.get_cell_pos()
                        r2, c2 = piece2.current_state.physics.get_cell_pos()
                        
                        # בדיקת התנגשות (אותו ריבוע)
                        if r1 == r2 and c1 == c2 and not self._is_same_team(piece1, piece2):
                            # לוגיקת אכילה פשוטה - הכלי השני נאכל
                            pieces_to_remove.append(piece2)
                            
                            print(f"{piece1.piece_id} captured {piece2.piece_id}")
                            
                            # פרסום אירוע אכילה
                            event = Event("piece_captured", {
                                "captured_piece": piece2.piece_id,
                                "capturing_piece": piece1.piece_id,
                                "position": (r1, c1)
                            })
                            self.event_bus.publish(event)
                            break
                    except Exception as e:
                        print(f"Error checking collision between pieces: {e}")
                        continue
            # הסרת הכלים שנאכלו
            for piece in pieces_to_remove:
                if piece in self.pieces:
                    self.pieces.remove(piece)
                    
        except Exception as e:
            print(f"Error resolving collisions: {e}")

    def _is_win(self) -> bool:
        """בדיקת תנאי ניצחון"""
        try:
            if self.game_over:
                return True
                
            # בדיקה אם נשארו כלים לכל צד
            white_pieces = [p for p in self.pieces if self._can_player_control_piece(1, p)]
            black_pieces = [p for p in self.pieces if self._can_player_control_piece(2, p)]
            
            # רק אם אחד הצדדים איבד את כל הכלים
            if len(white_pieces) == 0 and len(black_pieces) > 0:
                self.game_over = True
                self.winner = black_pieces[0]
                return True
            elif len(black_pieces) == 0 and len(white_pieces) > 0:
                self.game_over = True
                self.winner = white_pieces[0]
                return True
            elif len(white_pieces) == 0 and len(black_pieces) == 0:
                self.game_over = True
                self.winner = None  # תיקו
                return True
                
            return False
        except Exception as e:
            print(f"Error checking win condition: {e}")
            return False

    def _announce_win(self):
        """הכרזת המנצח"""
        try:
            if self.winner:
                winner_color = "White" if self._can_player_control_piece(1, self.winner) else "Black"
                print(f"Game Over! Winner: {winner_color} ({self.winner.piece_id})")
                
                if self.current_board and hasattr(self.current_board.img, 'put_text'):
                    win_text = f"Winner: {winner_color}!"
                    self.current_board.img.put_text(win_text, 
                                                   self.board.cell_W_pix * 2, 
                                                   self.board.cell_H_pix * 4, 
                                                   2.0, (0, 255, 0, 255), 3)
                    cv2.imshow(self.window_name, self.current_board.img.img)
                    cv2.waitKey(3000)
            else:
                print("Game Over! Draw!")
                
                if self.current_board and hasattr(self.current_board.img, 'put_text'):
                    draw_text = "Draw!"
                    self.current_board.img.put_text(draw_text,
                                                   self.board.cell_W_pix * 3,
                                                   self.board.cell_H_pix * 4,
                                                   2.0, (255, 255, 0, 255), 3)
                    cv2.imshow(self.window_name, self.current_board.img.img)
                    cv2.waitKey(3000)
        except Exception as e:
            print(f"Error announcing winner: {e}")