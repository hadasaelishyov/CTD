# import inspect
# import pathlib
# import queue, threading, time, cv2, math
# from typing import List, Dict, Tuple, Optional
# from Board   import Board
# from Bus.bus import EventBus, Event
# from Command import Command
# from Piece   import Piece
# from img     import Img

# class InvalidBoard(Exception): ...

# class Game:
#     def __init__(self, pieces: List[Piece], board: Board):
#         """Initialize the game with pieces, board, and optional event bus."""
#         self.pieces = pieces
#         self.board = board
#         self.event_bus = EventBus() if EventBus else None
#         self.user_input_queue = queue.Queue()
#         self.current_board = None
#         self.game_start_time = None
#         self.window_name = "Chess Game"
#         self.mouse_callback_active = False
        
#         # מצב המשחק
#         self.winner = None
#         self.game_over = False
        
#         # מיקומי שחקנים
#         self.player1_cursor = [0, 0]
#         self.player2_cursor = [0, 0]
#         self.player1_selected_piece = None
#         self.player2_selected_piece = None

#     def game_time_ms(self) -> int:
#         """Return the current game time in milliseconds."""
#         if self.game_start_time is None:
#             self.game_start_time = time.perf_counter()
#             return 0
#         return int((time.perf_counter() - self.game_start_time) * 1000)

#     def clone_board(self) -> Board:
#         return self.board.clone()

#     def start_user_input_thread(self):
#         """Start the user input thread for keyboard handling."""
#         if not self.mouse_callback_active:
#             cv2.namedWindow(self.window_name)
#             self.mouse_callback_active = True

#     def _handle_keyboard_input(self):
#         """Handle keyboard input for both players."""
#         key = cv2.waitKey(1) & 0xFF
        
#         if key == 255:  # אין מקש
#             return True
            
#         # שחקן 1 (חיצים + Enter)
#         if key == 82:  # חץ למעלה
#             self.player1_cursor[0] = min(self.board.H_cells - 1, self.player1_cursor[0] + 1)
#         elif key == 84:  # חץ למטה
#             self.player1_cursor[0] = max(0, self.player1_cursor[0] - 1)
#         elif key == 81:  # חץ שמאלה
#             self.player1_cursor[1] = max(0, self.player1_cursor[1] - 1)
#         elif key == 83:  # חץ ימינה
#             self.player1_cursor[1] = min(self.board.W_cells - 1, self.player1_cursor[1] + 1)
#         elif key == 13:  # Enter
#             self._handle_player_action(1, self.player1_cursor)
            
#         # שחקן 2 (WASD + רווח)
#         elif key == ord('w'):
#             self.player2_cursor[0] = min(self.board.H_cells - 1, self.player2_cursor[0] + 1)
#         elif key == ord('s'):
#             self.player2_cursor[0] = max(0, self.player2_cursor[0] - 1)
#         elif key == ord('a'):
#             self.player2_cursor[1] = max(0, self.player2_cursor[1] - 1)
#         elif key == ord('d'):
#             self.player2_cursor[1] = min(self.board.W_cells - 1, self.player2_cursor[1] + 1)
#         elif key == ord(' '):  # רווח
#             self._handle_player_action(2, self.player2_cursor)
            
#         # מקשי יציאה
#         elif key == ord('q') or key == 27:  # 'q' או ESC
#             return False
            
#         return True

#     def _handle_player_action(self, player_num: int, cursor_pos: list):
#         """Handle player action (select piece or move piece)."""
#         row, col = cursor_pos
#         piece_at_cursor = self._find_piece_at_cell(row, col)
        
#         if player_num == 1:
#             if self.player1_selected_piece is None:
#                 if piece_at_cursor and self._can_player_control_piece(1, piece_at_cursor):
#                     self.player1_selected_piece = piece_at_cursor
#                     print(f"Player 1 selected: {piece_at_cursor.piece_id}")
#             else:
#                 # בדיקה אם הכלי יכול לזוז (לא בקוד השהיה)
#                 now_ms = self.game_time_ms()
#                 if self.player1_selected_piece.current_state.physics.can_capture(now_ms):
#                     self._create_move_command(self.player1_selected_piece, cursor_pos)
#                 else:
#                     print("Piece is in cooldown, cannot move!")
#                 self.player1_selected_piece = None
                
#         elif player_num == 2:
#             if self.player2_selected_piece is None:
#                 if piece_at_cursor and self._can_player_control_piece(2, piece_at_cursor):
#                     self.player2_selected_piece = piece_at_cursor
#                     print(f"Player 2 selected: {piece_at_cursor.piece_id}")
#             else:
#                 now_ms = self.game_time_ms()
#                 if self.player2_selected_piece.current_state.physics.can_capture(now_ms):
#                     self._create_move_command(self.player2_selected_piece, cursor_pos)
#                 else:
#                     print("Piece is in cooldown, cannot move!")
#                 self.player2_selected_piece = None

#     def _can_player_control_piece(self, player_num: int, piece: Piece) -> bool:
#         """בדיקה אם השחקן יכול לשלוט בכלי (בהתבסס על ID או כל לוגיקה אחרת)"""
#         # זה רק דוגמה - תצטרך להתאים את זה לפי המבנה שלך
#         if player_num == 1:
#             return "white" in piece.piece_id.lower() or "w" in piece.piece_id.lower()
#         else:
#             return "black" in piece.piece_id.lower() or "b" in piece.piece_id.lower()

#     def _create_move_command(self, piece: Piece, target_pos: list):
#         """יצירת פקודת תזוזה"""
#         current_r, current_c = piece.current_state.physics.get_cell_pos()
#         current_pos = chr(ord('a') + int(current_c)) + str(int(current_r) + 1)
        
#         target_r, target_c = target_pos
#         target_chess_pos = chr(ord('a') + target_c) + str(target_r + 1)
        
#         cmd = Command(
#             timestamp=self.game_time_ms(),
#             piece_id=piece.piece_id,
#             type="Move",
#             params=[current_pos, target_chess_pos]
#         )
#         self.user_input_queue.put(cmd)
#         print(f"Move: {piece.piece_id} from {current_pos} to {target_chess_pos}")

#     def _find_piece_at_cell(self, r: int, c: int) -> Optional[Piece]:
#         """מציאת כלי במיקום נתון"""
#         for piece in self.pieces:
#             piece_r, piece_c = piece.current_state.physics.get_cell_pos()
#             if piece_r == r and piece_c == c:
#                 return piece
#         return None

#     def run(self):
#         """לולאת המשחק הראשית"""
#         # self.start_user_input_thread()
#         start_ms = self.game_time_ms()
        
#         for p in self.pieces:
#             p.reset(start_ms)

#         while not self._is_win():
#             now = self.game_time_ms()

#             # עדכון פיזיקה ואנימציות
#             for p in self.pieces:
#                 p.update(now)
#             # טיפול בקלט מקלדת
#             if not self._handle_keyboard_input():
#                 break

#             # טיפול בפקודות ממתינות
#             while not self.user_input_queue.empty():
#                 cmd: Command = self.user_input_queue.get()
#                 self._process_input(cmd)

#             # ציור
#             self._draw()
#             if not self._show():
#                 break

#             # בדיקת התנגשויות
#             self._resolve_collisions()

#             time.sleep(0.016)  # ~60 FPS

#         self._announce_win()
#         cv2.destroyAllWindows()

#     def _process_input(self, cmd: Command):
#         """עיבוד פקודה מהמשתמש"""
#         for piece in self.pieces:
#             if piece.piece_id == cmd.piece_id:
#                 piece.on_command(cmd, self.game_time_ms())
#                 if self.event_bus:
#                     event = Event("command_executed", {"command": cmd, "piece": piece})
#                     self.event_bus.publish(event)
#                 break

#     def _draw(self):
#         """ציור המצב הנוכחי"""
#         self.current_board = self.clone_board()
#         now_ms = self.game_time_ms()
        
#         for piece in self.pieces:
#             piece.draw_on_board(self.current_board, now_ms)
        
#         # ציור סמני השחקנים
#         self._draw_cursor(1, self.player1_cursor, (0, 255, 0))  # ירוק לשחקן 1
#         self._draw_cursor(2, self.player2_cursor, (0, 0, 255))  # אדום לשחקן 2
        
#         # ציור בחירות
#         if self.player1_selected_piece:
#             r, c = self.player1_selected_piece.current_state.physics.get_cell_pos()
#             self._draw_selection(r, c, (0, 255, 255))  # צהוב
            
#         if self.player2_selected_piece:
#             r, c = self.player2_selected_piece.current_state.physics.get_cell_pos()
#             self._draw_selection(r, c, (255, 0, 255))  # מגנטה

#     def _draw_cursor(self, player_num: int, cursor_pos: list, color: tuple):
#         """ציור סמן השחקן"""
#         row, col = cursor_pos
#         x = col * self.board.cell_W_pix
#         y = row * self.board.cell_H_pix
        
#         cv2.rectangle(self.current_board.img.img, (x, y),
#                      (x + self.board.cell_W_pix - 1, y + self.board.cell_H_pix - 1),
#                      color, 3)
        
#         self.current_board.img.put_text(str(player_num), x + 5, y + 25,
#                                        0.7, (*color, 255), 2)

#     def _draw_selection(self, row: int, col: int, color: tuple):
#         """ציור בחירת כלי"""
#         x = col * self.board.cell_W_pix
#         y = row * self.board.cell_H_pix
        
#         cv2.rectangle(self.current_board.img.img,
#                      (x + 2, y + 2),
#                      (x + self.board.cell_W_pix - 3, y + self.board.cell_H_pix - 3),
#                      color, 5)

#     def _show(self) -> bool:
#         """הצגת הפריים הנוכחי"""
#         if self.current_board is None or self.current_board.img.img is None:
#             return True
            
#         try:
#             cv2.imshow(self.window_name, self.current_board.img.img)
#             if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
#                 return False
#             return True
#         except cv2.error:
#             return False

#     def _resolve_collisions(self):
#         """פתרון התנגשויות ואכילות"""
#         now_ms = self.game_time_ms()
#         pieces_to_remove = []
        
#         for i, piece1 in enumerate(self.pieces):
#             for piece2 in self.pieces[i+1:]:
#                 r1, c1 = piece1.current_state.physics.get_cell_pos()
#                 r2, c2 = piece2.current_state.physics.get_cell_pos()
                
#                 # בדיקת התנגשות (אותו ריבוע)
#                 if r1 == r2 and c1 == c2:
#                     can_p1_capture = piece1.current_state.physics.can_capture(now_ms)
#                     can_p2_capture = piece2.current_state.physics.can_capture(now_ms)
#                     can_p1_be_captured = piece1.current_state.physics.can_be_captured(now_ms)
#                     can_p2_be_captured = piece2.current_state.physics.can_be_captured(now_ms)
                    
#                     # הכלי שהתחיל לזוז ראשון אוכל את השני
#                     p1_start = piece1.current_state.physics.start_time_ms or 0
#                     p2_start = piece2.current_state.physics.start_time_ms or 0
                    
#                     if can_p1_capture and can_p2_be_captured and p1_start < p2_start:
#                         pieces_to_remove.append(piece2)
#                         print(f"{piece1.piece_id} captured {piece2.piece_id}")
#                     elif can_p2_capture and can_p1_be_captured and p2_start < p1_start:
#                         pieces_to_remove.append(piece1)
#                         print(f"{piece2.piece_id} captured {piece1.piece_id}")
        
#         # הסרת הכלים שנאכלו
#         for piece in pieces_to_remove:
#             if piece in self.pieces:
#                 self.pieces.remove(piece)

#     def _is_win(self) -> bool:
#         """בדיקת תנאי ניצחון"""
#         if self.game_over:
#             return True
            
#         # חיפוש מלכים
#         kings = [p for p in self.pieces if "king" in p.piece_id.lower()]
        
#         if len(kings) <= 1:
#             self.game_over = True
#             if len(kings) == 1:
#                 self.winner = kings[0]
#             return True
            
#         return False

#     def _announce_win(self):
#         """הכרזת המנצח"""
#         if self.winner:
#             print(f"Game Over! Winner: {self.winner.piece_id}")
#             if self.current_board:
#                 self.current_board.img.put_text(f"Winner: {self.winner.piece_id}",
#                                                50, 50, 2.0, (0, 255, 0, 255), 3)
#                 cv2.imshow(self.window_name, self.current_board.img.img)
#                 cv2.waitKey(3000)
#         else:
#             print("Game Over! Draw!")
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
            if key == 82:  # חץ למעלה
                self.player1_cursor[0] = max(0, self.player1_cursor[0] - 1)
            elif key == 84:  # חץ למטה
                self.player1_cursor[0] = min(self.board.H_cells - 1, self.player1_cursor[0] + 1)
            elif key == 81:  # חץ שמאלה
                self.player1_cursor[1] = max(0, self.player1_cursor[1] - 1)
            elif key == 83:  # חץ ימינה
                self.player1_cursor[1] = min(self.board.W_cells - 1, self.player1_cursor[1] + 1)
            elif key == 13:  # Enter
                self._handle_player_action(1, self.player1_cursor)
            
        # שחקן 2 (WASD + רווח) - רק כשזה התור שלו
        elif current_player == 2:
            if key == ord('w'):
                self.player2_cursor[0] = max(0, self.player2_cursor[0] - 1)
            elif key == ord('s'):
                self.player2_cursor[0] = min(self.board.H_cells - 1, self.player2_cursor[0] + 1)
            elif key == ord('a'):
                self.player2_cursor[1] = max(0, self.player2_cursor[1] - 1)
            elif key == ord('d'):
                self.player2_cursor[1] = min(self.board.W_cells - 1, self.player2_cursor[1] + 1)
            elif key == ord(' '):  # רווח
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
        
        # בדיקה אם הכלי בקירור
        if not piece.current_state.physics.can_capture(now_ms):
            print("Piece is in cooldown, cannot move!")
            return False
        
        target_row, target_col = target_pos
        current_row, current_col = piece.current_state.physics.get_cell_pos()
        
        # בדיקה אם זה מהלך חוקי לפי כללי הכלי
        valid_moves = piece.current_state.moves.get_moves(current_row, current_col)
        if (target_row, target_col) not in valid_moves:
            print(f"Invalid move for {piece.piece_id}: ({current_row}, {current_col}) to ({target_row}, {target_col})")
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
            return any(identifier in piece_id_lower for identifier in ["white", "w_", "_w", "light"])
        else:  # שחקן שחור
            return any(identifier in piece_id_lower for identifier in ["black", "b_", "_b", "dark"])

    def _is_same_team(self, piece1: Piece, piece2: Piece) -> bool:
        """בדיקה אם שני כלים שייכים לאותה קבוצה"""
        p1_id = piece1.piece_id.lower()
        p2_id = piece2.piece_id.lower()
        
        # בדיקה אם שניהם לבנים
        p1_white = any(identifier in p1_id for identifier in ["white", "w_", "_w", "light"])
        p2_white = any(identifier in p2_id for identifier in ["white", "w_", "_w", "light"])
        
        # בדיקה אם שניהם שחורים
        p1_black = any(identifier in p1_id for identifier in ["black", "b_", "_b", "dark"])
        p2_black = any(identifier in p2_id for identifier in ["black", "b_", "_b", "dark"])
        
        return (p1_white and p2_white) or (p1_black and p2_black)

    def _create_move_command(self, piece: Piece, target_pos: list):
        """יצירת פקודת תזוזה"""
        current_r, current_c = piece.current_state.physics.get_cell_pos()
        
        target_r, target_c = target_pos
        
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

    def _find_piece_at_cell(self, r: int, c: int) -> Optional[Piece]:
        """מציאת כלי במיקום נתון"""
        for piece in self.pieces:
            piece_r, piece_c = piece.current_state.physics.get_cell_pos()
            if piece_r == r and piece_c == c:
                return piece
        return None

    def run(self):
        """לולאת המשחק הראשית"""
        self.start_user_input_thread()
        start_ms = self.game_time_ms()
        
        # איפוס כל הכלים
        for p in self.pieces:
            p.reset(start_ms)

        print(f"Game started! Current turn: {self.current_turn}")
        print("White player uses arrow keys + Enter")
        print("Black player uses WASD + Space")
        print("Press 'r' to reset selection, 'q' to quit")

        while not self._is_win():
            now = self.game_time_ms()

            # עדכון פיזיקה ואנימציות
            for p in self.pieces:
                p.update(now)

            # טיפול בקלט מקלדת
            if not self._handle_keyboard_input():
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

            # השהייה לשמירה על FPS
            time.sleep(0.016)  # ~60 FPS

        self._announce_win()
        cv2.destroyAllWindows()

    def _process_input(self, cmd: Command):
        """עיבוד פקודה מהמשתמש"""
        for piece in self.pieces:
            if piece.piece_id == cmd.piece_id:
                piece.on_command(cmd, self.game_time_ms())
                
                # פרסום אירוע תזוזה
                if cmd.type == "Move":
                    event = Event("piece_moved", {
                        "piece_id": piece.piece_id,
                        "command": cmd,
                        "position": cmd.params[1] if len(cmd.params) > 1 else None
                    })
                    self.event_bus.publish(event)
                break

    def _draw(self):
        """ציור המצב הנוכחי"""
        self.current_board = self.clone_board()
        now_ms = self.game_time_ms()
        
        # ציור כל הכלים
        for piece in self.pieces:
            piece.draw_on_board(self.current_board, now_ms)
        
        # ציור סמני השחקנים - רק של השחקן שבתור
        if self.current_turn == "white":
            self._draw_cursor(1, self.player1_cursor, (0, 255, 0))  # ירוק לשחקן 1
        else:
            self._draw_cursor(2, self.player2_cursor, (0, 0, 255))  # אדום לשחקן 2
        
        # ציור בחירות
        if self.player1_selected_piece and self.current_turn == "white":
            r, c = self.player1_selected_piece.current_state.physics.get_cell_pos()
            self._draw_selection(r, c, (0, 255, 255))  # צהוב
            self._draw_valid_moves(self.player1_selected_piece, (100, 255, 100))  # ירוק בהיר
            
        if self.player2_selected_piece and self.current_turn == "black":
            r, c = self.player2_selected_piece.current_state.physics.get_cell_pos()
            self._draw_selection(r, c, (255, 0, 255))  # מגנטה
            self._draw_valid_moves(self.player2_selected_piece, (255, 100, 100))  # אדום בהיר
        
        # הצגת מידע על המשחק
        self._draw_game_info()

    def _draw_cursor(self, player_num: int, cursor_pos: list, color: tuple):
        """ציור סמן השחקן"""
        row, col = cursor_pos
        x = col * self.board.cell_W_pix
        y = row * self.board.cell_H_pix
        
        # ציור מסגרת סמן
        cv2.rectangle(self.current_board.img.img, (x, y),
                     (x + self.board.cell_W_pix - 1, y + self.board.cell_H_pix - 1),
                     color, 3)
        
        # הצגת מספר השחקן
        self.current_board.img.put_text(str(player_num), x + 5, y + 25,
                                       0.7, (*color, 255), 2)

    def _draw_selection(self, row: int, col: int, color: tuple):
        """ציור בחירת כלי"""
        x = col * self.board.cell_W_pix
        y = row * self.board.cell_H_pix
        
        # מסגרת עבה לציון בחירה
        cv2.rectangle(self.current_board.img.img,
                     (x + 2, y + 2),
                     (x + self.board.cell_W_pix - 3, y + self.board.cell_H_pix - 3),
                     color, 5)

    def _draw_valid_moves(self, piece: Piece, color: tuple):
        """ציור המהלכים החוקיים לכלי שנבחר"""
        current_row, current_col = piece.current_state.physics.get_cell_pos()
        valid_moves = piece.current_state.moves.get_moves(current_row, current_col)
        
        for move_row, move_col in valid_moves:
            x = move_col * self.board.cell_W_pix
            y = move_row * self.board.cell_H_pix
            
            # ציור עיגול קטן במרכז התא
            center_x = x + self.board.cell_W_pix // 2
            center_y = y + self.board.cell_H_pix // 2
            cv2.circle(self.current_board.img.img, (center_x, center_y), 8, color, -1)

    def _draw_game_info(self):
        """ציור מידע על המשחק"""
        # מידע על התור הנוכחי
        turn_text = f"Turn: {self.current_turn.capitalize()}"
        self.current_board.img.put_text(turn_text, 10, 30, 1.0, (255, 255, 255, 255), 2)
        
        # מידע על הכלי הנבחר
        selected_piece = None
        if self.current_turn == "white" and self.player1_selected_piece:
            selected_piece = self.player1_selected_piece
        elif self.current_turn == "black" and self.player2_selected_piece:
            selected_piece = self.player2_selected_piece
            
        if selected_piece:
            selected_text = f"Selected: {selected_piece.piece_id}"
            self.current_board.img.put_text(selected_text, 10, 60, 0.8, (255, 255, 0, 255), 2)

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
                if r1 == r2 and c1 == c2 and not self._is_same_team(piece1, piece2):
                    can_p1_capture = piece1.current_state.physics.can_capture(now_ms)
                    can_p2_capture = piece2.current_state.physics.can_capture(now_ms)
                    can_p1_be_captured = piece1.current_state.physics.can_be_captured(now_ms)
                    can_p2_be_captured = piece2.current_state.physics.can_be_captured(now_ms)
                    
                    # הכלי שהתחיל לזוז ראשון אוכל את השני
                    p1_start = piece1.current_state.physics.start_time_ms or 0
                    p2_start = piece2.current_state.physics.start_time_ms or 0
                    
                    captured_piece = None
                    capturing_piece = None
                    
                    if can_p1_capture and can_p2_be_captured and p1_start < p2_start:
                        pieces_to_remove.append(piece2)
                        captured_piece = piece2
                        capturing_piece = piece1
                    elif can_p2_capture and can_p1_be_captured and p2_start < p1_start:
                        pieces_to_remove.append(piece1)
                        captured_piece = piece1
                        capturing_piece = piece2
                    
                    if captured_piece and capturing_piece:
                        print(f"{capturing_piece.piece_id} captured {captured_piece.piece_id}")
                        
                        # פרסום אירוע אכילה
                        event = Event("piece_captured", {
                            "captured_piece": captured_piece.piece_id,
                            "capturing_piece": capturing_piece.piece_id,
                            "position": (r1, c1)
                        })
                        self.event_bus.publish(event)
        
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
            elif len(kings) == 0:
                self.winner = None  # תיקו
            return True
        
        # בדיקה אם נשארו כלים לכל צד
        white_pieces = [p for p in self.pieces if self._can_player_control_piece(1, p)]
        black_pieces = [p for p in self.pieces if self._can_player_control_piece(2, p)]
        
        if len(white_pieces) == 0:
            self.game_over = True
            self.winner = black_pieces[0] if black_pieces else None
            return True
        elif len(black_pieces) == 0:
            self.game_over = True
            self.winner = white_pieces[0] if white_pieces else None
            return True
            
        return False

    def _announce_win(self):
        """הכרזת המנצח"""
        if self.winner:
            winner_color = "White" if self._can_player_control_piece(1, self.winner) else "Black"
            print(f"Game Over! Winner: {winner_color} ({self.winner.piece_id})")
            
            if self.current_board:
                win_text = f"Winner: {winner_color}!"
                self.current_board.img.put_text(win_text, 
                                               self.board.cell_W_pix * 2, 
                                               self.board.cell_H_pix * 4, 
                                               2.0, (0, 255, 0, 255), 3)
                cv2.imshow(self.window_name, self.current_board.img.img)
                cv2.waitKey(3000)
        else:
            print("Game Over! Draw!")
            
            if self.current_board:
                draw_text = "Draw!"
                self.current_board.img.put_text(draw_text,
                                               self.board.cell_W_pix * 3,
                                               self.board.cell_H_pix * 4,
                                               2.0, (255, 255, 0, 255), 3)
                cv2.imshow(self.window_name, self.current_board.img.img)
                cv2.waitKey(3000)