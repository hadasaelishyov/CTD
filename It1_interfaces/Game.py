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
        
        # מצב המשחק - הסרת מערכת התורות
        self.winner = None
        self.game_over = False
        
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
        key = cv2.waitKey(1) & 0xFF
        key = cv2.waitKey(1) & 0xFF
        if key == 0 or key == 224:  # אם זה מקש מיוחד
            key = cv2.waitKey(1) & 0xFF  # קלט נוסף - הקוד האמיתי
        if key != 255:
            print(f"Key pressed: {key}")

        if key == 255:  # No key pressed
            return True

        # Player 1 (Arrow keys + Enter + Shift for jump)
        if key == 82 or key == 65362:  # Up arrow (תיקון עבור מערכות שונות)
            self.player1_cursor[0] = max(0, self.player1_cursor[0] - 1)
        elif key == 84 or key == 65364: # Down arrow
            self.player1_cursor[0] = min(self.board.H_cells - 1, self.player1_cursor[0] + 1)
        elif key == 81 or key == 65361: # Left arrow
            self.player1_cursor[1] = max(0, self.player1_cursor[1] - 1)
        elif key == 83 or key == 65363: # Right arrow
            self.player1_cursor[1] = min(self.board.W_cells - 1, self.player1_cursor[1] + 1)
        elif key == 13 or key == 10:  # Enter - Regular move
            self._handle_player_action(1, self.player1_cursor, False)
        elif key == ord('j') or key == ord('J'):  # 'j' key for Player 1 jump
            self._handle_player_action(1, self.player1_cursor, True)

        # Player 2 (WASD + Space + 'K' for jump)
        elif key == ord('w') or key == ord('W'):  # W
            self.player2_cursor[0] = max(0, self.player2_cursor[0] - 1)
        elif key == ord('s') or key == ord('S'):  # S
            self.player2_cursor[0] = min(self.board.H_cells - 1, self.player2_cursor[0] + 1)
        elif key == ord('a') or key == ord('A'):  # A
            self.player2_cursor[1] = max(0, self.player2_cursor[1] - 1)
        elif key == ord('d') or key == ord('D'):  # D
            self.player2_cursor[1] = min(self.board.W_cells - 1, self.player2_cursor[1] + 1)
        elif key == ord(' '):  # Space - Regular move
            self._handle_player_action(2, self.player2_cursor, False)
        elif key == ord('k') or key == ord('K'):  # 'k' key for Player 2 jump
            self._handle_player_action(2, self.player2_cursor, True)

        # Exit keys - always active
        elif key == ord('q') or key == ord('Q') or key == 27:  # 'q' or ESC
            return False

        # Key to reset selection
        elif key == ord('r') or key == ord('R'):
            self.player1_selected_piece = None
            self.player2_selected_piece = None
            print("Selection reset")
            
        return True

    
    def _handle_player_action(self, player_num: int, cursor_pos: list, is_jump: bool = False):
        """Handle player action (select piece or move piece) - REMOVED TURN CHECK!"""
        row, col = cursor_pos
        piece_at_cursor = self._find_piece_at_cell(row, col)
        
        if player_num == 1:
            if self.player1_selected_piece is None:
                # בחירת כלי
                if piece_at_cursor and self._can_player_control_piece(1, piece_at_cursor):
                    # בדיקה אם הכלי לא בהשהיה
                    if self._is_piece_in_cooldown(piece_at_cursor):
                        print("Piece is in cooldown!")
                        return
                    
                    self.player1_selected_piece = piece_at_cursor
                    print(f"Player 1 selected: {piece_at_cursor.piece_id}")
                else:
                    print("No valid piece to select at this position")
            else:
                # ניסיון להזיז כלי
                if self._attempt_move(self.player1_selected_piece, cursor_pos, is_jump):
                    self.player1_selected_piece = None
                else:
                    # אם המהלך לא חוקי, בדוק אם רוצים לבחור כלי אחר
                    if piece_at_cursor and self._can_player_control_piece(1, piece_at_cursor):
                        if not self._is_piece_in_cooldown(piece_at_cursor):
                            self.player1_selected_piece = piece_at_cursor
                            print(f"Player 1 selected: {piece_at_cursor.piece_id}")
                    else:
                        print("Invalid move!")
                        self.player1_selected_piece = None
                
        elif player_num == 2:
            if self.player2_selected_piece is None:
                # בחירת כלי
                if piece_at_cursor and self._can_player_control_piece(2, piece_at_cursor):
                    # בדיקה אם הכלי לא בהשהיה
                    if self._is_piece_in_cooldown(piece_at_cursor):
                        print("Piece is in cooldown!")
                        return
                    
                    self.player2_selected_piece = piece_at_cursor
                    print(f"Player 2 selected: {piece_at_cursor.piece_id}")
                else:
                    print("No valid piece to select at this position")
            else:
                # ניסיון להזיז כלי
                if self._attempt_move(self.player2_selected_piece, cursor_pos, is_jump):
                    self.player2_selected_piece = None
                else:
                    # אם המהלך לא חוקי, בדוק אם רוצים לבחור כלי אחר
                    if piece_at_cursor and self._can_player_control_piece(2, piece_at_cursor):
                        if not self._is_piece_in_cooldown(piece_at_cursor):
                            self.player2_selected_piece = piece_at_cursor
                            print(f"Player 2 selected: {piece_at_cursor.piece_id}")
                    else:
                        print("Invalid move!")
                        self.player2_selected_piece = None

    def _is_piece_in_cooldown(self, piece: Piece) -> bool:
        """בדיקה אם הכלי במצב השהיה"""
        now_ms = self.game_time_ms()
        return hasattr(piece, 'cooldown_end_time') and now_ms < piece.cooldown_end_time
    
    def _attempt_move(self, piece: Piece, target_pos: list, is_jump: bool = False) -> bool:
        """ניסיון להזיז כלי - עם תמיכה בקפיצה"""
        now_ms = self.game_time_ms()
        
        if not hasattr(piece, 'current_state') or not piece.current_state or \
        not hasattr(piece.current_state, 'physics') or not piece.current_state.physics:
            print("Piece has no valid state or physics!")
            return False
            
        if self._is_piece_in_cooldown(piece):
            remaining_time = (piece.cooldown_end_time - now_ms) / 1000.0
            print(f"{piece.piece_id} is in cooldown, {remaining_time:.1f}s remaining!")
            return False
            
        target_row, target_col = target_pos
        
        try:
            current_row, current_col = piece.current_state.physics.get_cell_pos()
        except Exception as e:
            print(f"Error getting piece position: {e}")
            return False
            
        if current_row == target_row and current_col == target_col:
            print("Cannot move to same position!")
            return False
            
        if not (0 <= target_row < self.board.H_cells and 0 <= target_col < self.board.W_cells):
            print("Move is out of board bounds!")
            return False

        # חישוב מרחק המהלך
        distance = abs(target_row - current_row) + abs(target_col - current_col)
        
        # הגבלת מרחק המהלך (כלי יכול לזוז רק משבצת אחת בכל כיוון)
        if distance > 1 and not is_jump:
            print("Regular move can only be to adjacent cell!")
            return False
        
        # עבור קפיצה, אפשר מרחק גדול יותר אבל מוגבל
        if is_jump and distance > 3:
            print("Jump distance too far! Maximum 3 cells.")
            return False
            
        # בדיקה אם יש כלי יריב במיקום היעד
        target_piece = self._find_piece_at_cell(target_row, target_col)
        
        if target_piece:
            if self._is_same_team(piece, target_piece):
                print("Cannot capture your own piece!")
                return False
            elif is_jump:
                print(f"{piece.piece_id} is jumping to capture {target_piece.piece_id}.")
            else:
                print(f"{piece.piece_id} will capture {target_piece.piece_id}.")
        
        self._create_move_command(piece, target_pos, is_jump)
        
        # הגדרת זמן השהיה
        cooldown_duration = 1000 if is_jump else 4000  # 1 שנייה לקפיצה, 4 שניות למהלך רגיל
        piece.cooldown_end_time = now_ms + cooldown_duration
        
        # הגדרת timestamp למהלך (לצורך התנגשויות)
        piece.last_move_timestamp = now_ms
        
        print(f"{piece.piece_id} {'jumped' if is_jump else 'moved'} to ({target_row}, {target_col})")
        return True

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
        p2_black = any(identifier in p2_id for identifier in ["black", "b_", "_b", "dark", "bb", "kb", "nb", "pb", "qb", "rb"])
        
        return (p1_white and p2_white) or (p1_black and p2_black)

    def _create_move_command(self, piece: Piece, target_pos: list, is_jump: bool = False):
        """יצירת פקודת תזוזה עם תמיכה בקפיצה"""
        try:
            current_r, current_c = piece.current_state.physics.get_cell_pos()
            target_r, target_c = target_pos
            
            # עדכון מיקום הכלי
            piece.current_state.physics.row = target_r
            piece.current_state.physics.col = target_c
            
            # אתחול מאפייני קפיצה
            if not hasattr(piece, 'is_jumping'):
                piece.is_jumping = False
            if not hasattr(piece, 'jump_end_time'):
                piece.jump_end_time = 0
            
            piece.is_jumping = is_jump
            if is_jump:
                piece.jump_end_time = self.game_time_ms() + 500  # קפיצה נמשכת חצי שנייה
            else:
                piece.jump_end_time = 0
            
            # המרה לסימון שחמט
            current_pos_chess = chr(ord('a') + int(current_c)) + str(int(current_r) + 1)
            target_chess_pos = chr(ord('a') + target_c) + str(target_r + 1)
            
            cmd_type = "Jump" if is_jump else "Move"
            cmd = Command(
                timestamp=self.game_time_ms(),
                piece_id=piece.piece_id,
                type=cmd_type,
                params=[current_pos_chess, target_chess_pos]
            )
            
            self.user_input_queue.put(cmd)
            print(f"{cmd_type} command created: {piece.piece_id} from {current_pos_chess} to {target_chess_pos}")
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
        """לולאת המשחק הראשית - ללא בדיקות תור"""
        self.start_user_input_thread()
        start_ms = self.game_time_ms()
        
        # איפוס ודא שכל הכלים מאותחלים עם מאפייני קירור וקפיצה
        for p in self.pieces:
            try:
                if hasattr(p, 'reset'):
                    p.reset(start_ms)
                # ודא קיום מאפיינים אלו על אובייקט Piece
                if not hasattr(p, 'cooldown_end_time'):
                    p.cooldown_end_time = 0
                if not hasattr(p, 'is_jumping'):
                    p.is_jumping = False
                if not hasattr(p, 'jump_end_time'):
                    p.jump_end_time = 0
                if not hasattr(p, 'last_move_timestamp'):
                    p.last_move_timestamp = 0
            except Exception as e:
                print(f"Error resetting piece {p.piece_id}: {e}")

        print("Simultaneous Chess Game started!")
        print("White player (Player 1): Arrow keys + Enter (move) + J (jump)")
        print("Black player (Player 2): WASD + Space (move) + K (jump)")
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
                    if frame_count % (self.target_fps * 10) == 0:  # כל 10 שניות
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

            # בדיקת התנגשויות לפני הציור
            try:
                self._resolve_collisions()
            except Exception as e:
                print(f"Error resolving collisions: {e}")

            # ציור
            try:
                self._draw()
                if not self._show():
                    break
            except Exception as e:
                print(f"Error drawing/showing frame: {e}")

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
                    if cmd.type in ["Move", "Jump"]:
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
        """ציור המצב הנוכחי - עם תמיכה בקפיצות"""
        try:
            self.current_board = self.clone_board()
            now_ms = self.game_time_ms()
            
            # ציור כל הכלים
            for piece in self.pieces:
                try:
                    if hasattr(piece, 'draw_on_board'):
                        piece.draw_on_board(self.current_board, now_ms)
                    else:
                        self._draw_demo_piece(piece, now_ms)
                except Exception as e:
                    print(f"Error drawing piece {piece.piece_id}: {e}")
            
            # ציור סמני השחקנים
            self._draw_cursor(1, self.player1_cursor, (0, 255, 0))  # ירוק לשחקן 1
            self._draw_cursor(2, self.player2_cursor, (0, 0, 255))  # אדום לשחקן 2
            
            # ציור בחירות
            if self.player1_selected_piece:
                try:
                    r, c = self.player1_selected_piece.current_state.physics.get_cell_pos()
                    self._draw_selection(r, c, (0, 255, 255))  # צהוב
                except Exception as e:
                    print(f"Error drawing player 1 selection: {e}")
                    
            if self.player2_selected_piece:
                try:
                    r, c = self.player2_selected_piece.current_state.physics.get_cell_pos()
                    self._draw_selection(r, c, (255, 0, 255))  # מגנטה
                except Exception as e:
                    print(f"Error drawing player 2 selection: {e}")
            
            # הצגת מידע על המשחק
            self._draw_game_info()
            
        except Exception as e:
            print(f"Error in draw method: {e}")

    def _draw_demo_piece(self, piece: Piece, now_ms: int):
        """ציור משופר לכלי דמו עם אינדיקציה לקפיצה וקירור"""
        try:
            r, c = piece.current_state.physics.get_cell_pos()
            x = c * self.current_board.cell_W_pix + 10
            y = r * self.current_board.cell_H_pix + 10
            
            # בדיקה אם הכלי קופץ
            is_jumping = hasattr(piece, 'is_jumping') and piece.is_jumping
            
            # בדיקה אם הכלי בהשהיה
            in_cooldown = self._is_piece_in_cooldown(piece)
            
            # צבע לפי השחקן ומצב
            if self._can_player_control_piece(1, piece):
                if in_cooldown:
                    color = (150, 150, 150)  # אפור - בהשהיה
                    border_color = (100, 100, 100)
                else:
                    color = (255, 255, 255)  # לבן
                    border_color = (200, 200, 200)
            else:
                if in_cooldown:
                    color = (80, 80, 80)  # אפור כהה - בהשהיה
                    border_color = (50, 50, 50)
                else:
                    color = (40, 40, 40)  # כמעט שחור
                    border_color = (100, 100, 100)
            
            # אם קופץ, הזז מעט למעלה וצייר צללית
            jump_offset = 0
            if is_jumping:
                jump_offset = -15
                # צללית תחתית
                shadow_center = (
                    c * self.current_board.cell_W_pix + self.current_board.cell_W_pix // 2, 
                    r * self.current_board.cell_H_pix + self.current_board.cell_H_pix // 2
                )
                cv2.circle(self.current_board.img.img, shadow_center, 30, (100, 100, 100), 3)
            
            # ציור צללית רגילה
            if not is_jumping:
                shadow_offset = 3
                cv2.rectangle(self.current_board.img.img, 
                            (x + shadow_offset, y + shadow_offset), 
                            (x + 60 + shadow_offset, y + 60 + shadow_offset), 
                            (20, 20, 20), -1)
            
            # ציור הכלי עצמו (עם היסט קפיצה)
            piece_y = y + jump_offset
            cv2.rectangle(self.current_board.img.img, 
                        (x, piece_y), 
                        (x + 60, piece_y + 60), 
                        color, -1)
            cv2.rectangle(self.current_board.img.img, 
                        (x, piece_y), 
                        (x + 60, piece_y + 60), 
                        border_color, 2)
                            
            # הוספת טקסט
            piece_name = piece.piece_id
            if "_" in piece_name:
                piece_type = piece_name.split('_')[0][:2].upper()
            else:
                piece_type = piece_name[:2].upper()
            
            text_color = (0, 0, 0) if self._can_player_control_piece(1, piece) else (255, 255, 255)
            
            cv2.putText(self.current_board.img.img, piece_type, 
                        (x + 15, piece_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.6, text_color, 2)
                            
            # אינדיקטור קפיצה
            if is_jumping:
                cv2.putText(self.current_board.img.img, "JUMP", 
                            (x + 10, piece_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                            0.4, (0, 255, 255), 1)
                            
            # אינדיקטור השהיה עם זמן נותר
            if in_cooldown:
                remaining_time = max(0, (piece.cooldown_end_time - now_ms) / 1000.0)
                cooldown_text = f"{remaining_time:.1f}s"
                cv2.putText(self.current_board.img.img, cooldown_text, 
                            (x + 5, piece_y + 75), cv2.FONT_HERSHEY_SIMPLEX, 
                            0.35, (255, 100, 100), 1)
                        
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
        """ציור מידע משופר על המשחק"""
        try:
            # מידע כללי על המשחק
            game_text = "Simultaneous Chess - No Turns!"
            
            # ציור רקע לטקסט
            cv2.rectangle(self.current_board.img.img, (5, 5), (350, 45), (0, 0, 0), -1)
            cv2.rectangle(self.current_board.img.img, (5, 5), (350, 45), (255, 255, 255), 2)
            
            cv2.putText(self.current_board.img.img, game_text, 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.7, (255, 255, 255), 2)
            
            # הוראות משחק
            instructions = [
                "P1: Arrows+Enter+J(jump) | P2: WASD+Space+K(jump)",
                "Cooldown: 4s move, 1s jump | R=reset, Q=quit"
            ]
            
            y_offset = 55
            for instruction in instructions:
                cv2.rectangle(self.current_board.img.img, (5, y_offset), (len(instruction) * 8 + 10, y_offset + 20), (30, 30, 30), -1)
                cv2.putText(self.current_board.img.img, instruction, 
                        (10, y_offset + 15), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.4, (200, 200, 200), 1)
                y_offset += 25
            
            # מידע על הכלים הנבחרים
            if self.player1_selected_piece:
                selected_text = f"P1 Selected: {self.player1_selected_piece.piece_id}"
                in_cooldown = self._is_piece_in_cooldown(self.player1_selected_piece)
                color = (100, 100, 100) if in_cooldown else (0, 150, 0)
                
                cv2.rectangle(self.current_board.img.img, (5, y_offset), (300, y_offset + 25), color, -1)
                cv2.putText(self.current_board.img.img, selected_text, 
                        (10, y_offset + 18), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, (255, 255, 255), 1)
                y_offset += 30
                
            if self.player2_selected_piece:
                selected_text = f"P2 Selected: {self.player2_selected_piece.piece_id}"
                in_cooldown = self._is_piece_in_cooldown(self.player2_selected_piece)
                color = (100, 100, 100) if in_cooldown else (150, 0, 0)
                
                cv2.rectangle(self.current_board.img.img, (5, y_offset), (300, y_offset + 25), color, -1)
                cv2.putText(self.current_board.img.img, selected_text, 
                        (10, y_offset + 18), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, (255, 255, 255), 1)
                y_offset += 30
            
            # הצגת מספר הכלים שנותרו
            white_pieces = [p for p in self.pieces if self._can_player_control_piece(1, p)]
            black_pieces = [p for p in self.pieces if self._can_player_control_piece(2, p)]
            
            pieces_info = f"White: {len(white_pieces)} pieces | Black: {len(black_pieces)} pieces"
            cv2.putText(self.current_board.img.img, pieces_info, 
                    (10, y_offset + 18), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, (200, 200, 200), 1)
            
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
        """פתרון התנגשויות ואכילות - עם תמיכה בקפיצות"""
        now_ms = self.game_time_ms()
        pieces_to_remove = []
        
        # שלב 1: עדכון סטטוס קפיצה של כל הכלים
        for piece in self.pieces:
            if hasattr(piece, 'is_jumping') and piece.is_jumping and \
            hasattr(piece, 'jump_end_time') and now_ms >= piece.jump_end_time:
                piece.is_jumping = False
                print(f"{piece.piece_id} landed from jump.")
        
        # שלב 2: בדיקת התנגשויות - רק כלים שלא קופצים
        piece_positions: Dict[Tuple[int, int], List[Piece]] = {}
        
        for piece in self.pieces:
            if not hasattr(piece, 'current_state') or not piece.current_state or \
            not hasattr(piece.current_state, 'physics'):
                continue
            
            try:
                r, c = piece.current_state.physics.get_cell_pos()
            except:
                continue
                
            # כלים קופצים אינם נמצאים על הלוח לצורך התנגשויות רגילות
            if hasattr(piece, 'is_jumping') and piece.is_jumping:
                continue
            
            if (r, c) not in piece_positions:
                piece_positions[(r, c)] = []
            piece_positions[(r, c)].append(piece)

        # בדיקת התנגשויות במיקומים שבהם יש יותר מכלי אחד
        for pos, occupying_pieces in piece_positions.items():
            if len(occupying_pieces) > 1:
                # מיון הכלים לפי זמן המהלך האחרון - הראשון שהתחיל לזוז מנצח
                occupying_pieces.sort(key=lambda p: getattr(p, 'last_move_timestamp', 0))
                
                winner_piece = occupying_pieces[0]  # הכלי עם הזמן הקטן ביותר (התחיל ראשון)
                
                # הסרת כל הכלים האחרים שאינם מאותו צוות
                for piece_to_check in occupying_pieces[1:]:
                    if not self._is_same_team(winner_piece, piece_to_check):
                        if piece_to_check not in pieces_to_remove:
                            pieces_to_remove.append(piece_to_check)
                            print(f"{winner_piece.piece_id} captured {piece_to_check.piece_id} at {pos}")
                            
                            event = Event("piece_captured", {
                                "captured_piece": piece_to_check.piece_id,
                                "capturing_piece": winner_piece.piece_id,
                                "position": pos
                            })
                            self.event_bus.publish(event)
        
        # הסרת הכלים שנאכלו
        for piece in pieces_to_remove:
            if piece in self.pieces:
                # ביטול בחירה אם הכלי שנאכל היה נבחר
                if self.player1_selected_piece == piece:
                    self.player1_selected_piece = None
                    print("Player 1's selected piece was captured!")
                if self.player2_selected_piece == piece:
                    self.player2_selected_piece = None
                    print("Player 2's selected piece was captured!")
                
                self.pieces.remove(piece)

    def _get_player_num_for_piece(self, piece: Piece) -> int:
        """פונקציית עזר למציאת מספר השחקן השולט בכלי"""
        if self._can_player_control_piece(1, piece):
            return 1
        elif self._can_player_control_piece(2, piece):
            return 2
        return 0 # כלי ניטרלי או לא מזוהה

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
