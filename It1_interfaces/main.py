import pathlib
import cv2
import numpy as np
import sys
import os
from Game import Game
from Board import Board
from img import Img

# Import עם טיפול בשגיאות
try:
    from PieceFactory import PieceFactory
    PIECE_FACTORY_AVAILABLE = True
except ImportError:
    print("Warning: PieceFactory not available. Will create simple test pieces.")
    PIECE_FACTORY_AVAILABLE = False

try:
    from Piece import Piece
    PIECE_CLASS_AVAILABLE = True
except ImportError:
    print("Warning: Piece class not available.")
    PIECE_CLASS_AVAILABLE = False

def create_board() -> Board:
    """יצירת לוח שחמט 8x8 עם תאים בגודל 80x80 פיקסלים"""
    
    # יצירת תמונה בסיסית ללוח
    cell_size = 80  # גודל תא מעט יותר גדול לנראות טובה יותר
    board_width = 8 * cell_size
    board_height = 8 * cell_size
    
    # יצירת תמונת לוח שחמט עם צבעים לסירוגין
    board_img = np.zeros((board_height, board_width, 4), dtype=np.uint8)
    
    # צבעים משופרים ללוח שחמט
    light_color = [240, 217, 181, 255]  # בז' בהיר
    dark_color = [181, 136, 99, 255]    # חום
    
    for row in range(8):
        for col in range(8):
            color = light_color if (row + col) % 2 == 0 else dark_color
            y_start = row * cell_size
            y_end = (row + 1) * cell_size
            x_start = col * cell_size
            x_end = (col + 1) * cell_size
            
            board_img[y_start:y_end, x_start:x_end] = color
    
    # הוספת מספרי שורות ואותיות עמודות (אופציונלי)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    text_color = (60, 60, 60, 255)  # אפור כהה
    
    # אותיות עמודות (a-h)
    for col in range(8):
        letter = chr(ord('a') + col)
        x = col * cell_size + cell_size // 2 - 5
        y = board_height - 5
        cv2.putText(board_img, letter, (x, y), font, font_scale, text_color, font_thickness)
    
    # מספרי שורות (1-8)
    for row in range(8):
        number = str(8 - row)  # שחמט מתחיל מ-1 למטה ו-8 למעלה
        x = 5
        y = row * cell_size + cell_size // 2 + 5
        cv2.putText(board_img, number, (x, y), font, font_scale, text_color, font_thickness)
    
    # יצירת אובייקט Img
    img_obj = Img()
    img_obj.img = board_img
    
    return Board(
        cell_W_pix=cell_size,
        cell_H_pix=cell_size,
        W_cells=8,
        H_cells=8,
        img=img_obj
    )

class SimplePhysics:
    """מחלקת פיזיקה פשוטה לכלי בדיקה"""
    def __init__(self, board, init_row, init_col):
        self.board = board
        self.cell_row = init_row
        self.cell_col = init_col
        self.cooldown_start_ms = 0
        self.cooldown_duration_ms = 0
    
    def get_cell_pos(self):
        """מחזיר מיקום בתאים (row, col)"""
        return int(self.cell_row), int(self.cell_col)
    
    def get_pos(self):
        """מחזיר מיקום מדויק (עבור ציור)"""
        return float(self.cell_row), float(self.cell_col)
    
    def set_cell_pos(self, row, col):
        """עדכון מיקום"""
        self.cell_row = row
        self.cell_col = col
    
    def can_capture(self, now_ms):
        """בדיקה אם הכלי יכול לבצע פעולה"""
        return now_ms >= (self.cooldown_start_ms + self.cooldown_duration_ms)
    
    def can_be_captured(self, now_ms):
        """בדיקה אם הכלי יכול להיאכל"""
        return self.can_capture(now_ms)

class SimpleGraphics:
    """מחלקת גרפיקה פשוטה לכלי בדיקה"""
    def __init__(self, piece_id):
        self.piece_id = piece_id
    
    def get_img(self):
        """מחזיר אובייקט דמה לציור"""
        return self

    def draw_on(self, target_img, x, y):
        """ציור הכלי על הלוח"""
        cell_size = 80
        
        # קביעת צבע לפי הכלי
        if 'white' in self.piece_id.lower() or 'w_' in self.piece_id.lower():
            color = (255, 255, 255, 255)  # לבן
            text_color = (0, 0, 0, 255)   # טקסט שחור
        else:
            color = (50, 50, 50, 255)     # כהה
            text_color = (255, 255, 255, 255)  # טקסט לבן
        
        # ציור עיגול לכלי
        center_x = x + cell_size // 2
        center_y = y + cell_size // 2
        radius = cell_size // 3
        
        try:
            cv2.circle(target_img.img, (center_x, center_y), radius, color, -1)
            cv2.circle(target_img.img, (center_x, center_y), radius, (0, 0, 0, 255), 2)
            
            # הוספת טקסט זיהוי
            if 'king' in self.piece_id.lower():
                symbol = 'K'
            elif 'queen' in self.piece_id.lower():
                symbol = 'Q'
            elif 'rook' in self.piece_id.lower():
                symbol = 'R'
            elif 'bishop' in self.piece_id.lower():
                symbol = 'B'
            elif 'knight' in self.piece_id.lower():
                symbol = 'N'
            elif 'pawn' in self.piece_id.lower():
                symbol = 'P'
            else:
                symbol = '?'
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(symbol, font, 0.8, 2)[0]
            text_x = center_x - text_size[0] // 2
            text_y = center_y + text_size[1] // 2
            
            cv2.putText(target_img.img, symbol, (text_x, text_y), font, 0.8, text_color, 2)
        except Exception as e:
            print(f"Error drawing piece: {e}")

class SimpleState:
    """מחלקת מצב פשוטה לכלי בדיקה"""
    def __init__(self, physics, graphics):
        self.physics = physics
        self.graphics = graphics
        self.current_command = None
    
    def get_state_after_command(self, cmd, now_ms):
        """עדכון מצב לאחר פקודה"""
        if cmd.type == "Move" and len(cmd.params) >= 2:
            target_pos = cmd.params[1]  # פורמט: "a1", "b2" וכו'
            
            # המרה מסימון שחמט לקואורדינטות
            if len(target_pos) >= 2:
                col = ord(target_pos[0].lower()) - ord('a')
                row = int(target_pos[1]) - 1
                
                if 0 <= row < 8 and 0 <= col < 8:
                    self.physics.set_cell_pos(row, col)
                    print(f"Moved {cmd.piece_id} to {target_pos} ({row}, {col})")
        
        return self
    
    def update(self, now_ms):
        """עדכון כללי של המצב"""
        return self
    
    def reset(self, reset_cmd):
        """איפוס המצב"""
        self.current_command = None

def create_simple_test_pieces(board: Board) -> list:
    """יצירת כלים פשוטים לבדיקה"""
    
    pieces = []
    
    if not PIECE_CLASS_AVAILABLE:
        print("Error: Cannot create pieces without Piece class")
        return pieces
    
    try:
        from Piece import Piece
        
        # מערך כלים בסיסי לשחמט
        piece_definitions = [
            # כלים לבנים
            ("white_king", 7, 4),
            ("white_queen", 7, 3),
            ("white_rook_1", 7, 0),
            ("white_rook_2", 7, 7),
            ("white_bishop_1", 7, 2),
            ("white_bishop_2", 7, 5),
            ("white_knight_1", 7, 1),
            ("white_knight_2", 7, 6),
            ("white_pawn_1", 6, 0),
            ("white_pawn_2", 6, 1),
            ("white_pawn_3", 6, 2),
            ("white_pawn_4", 6, 3),
            ("white_pawn_5", 6, 4),
            ("white_pawn_6", 6, 5),
            ("white_pawn_7", 6, 6),
            ("white_pawn_8", 6, 7),
            
            # כלים שחורים
            ("black_king", 0, 4),
            ("black_queen", 0, 3),
            ("black_rook_1", 0, 0),
            ("black_rook_2", 0, 7),
            ("black_bishop_1", 0, 2),
            ("black_bishop_2", 0, 5),
            ("black_knight_1", 0, 1),
            ("black_knight_2", 0, 6),
            ("black_pawn_1", 1, 0),
            ("black_pawn_2", 1, 1),
            ("black_pawn_3", 1, 2),
            ("black_pawn_4", 1, 3),
            ("black_pawn_5", 1, 4),
            ("black_pawn_6", 1, 5),
            ("black_pawn_7", 1, 6),
            ("black_pawn_8", 1, 7),
        ]
        
        for piece_id, row, col in piece_definitions:
            # יצירת רכיבי הכלי
            physics = SimplePhysics(board, row, col)
            graphics = SimpleGraphics(piece_id)
            state = SimpleState(physics, graphics)
            
            # יצירת הכלי
            piece = Piece(piece_id, state)
            pieces.append(piece)
        
        print(f"Created {len(pieces)} simple test pieces")
        
    except Exception as e:
        print(f"Failed to create simple test pieces: {e}")
        import traceback
        traceback.print_exc()
    
    return pieces

def create_pieces_with_factory(board: Board) -> list:
    """יצירת כלים באמצעות PieceFactory"""
    
    pieces = []
    pieces_root = pathlib.Path("pieces")
    
    if not pieces_root.exists():
        print(f"Pieces directory not found at {pieces_root}")
        return pieces
    
    try:
        piece_factory = PieceFactory(board, pieces_root)
        
        # בדיקה אילו סוגי כלים קיימים
        available_piece_types = []
        for piece_dir in pieces_root.iterdir():
            if piece_dir.is_dir():
                available_piece_types.append(piece_dir.name)
        
        print(f"Available piece types: {available_piece_types}")
        
        if not available_piece_types:
            print("No piece types found in pieces directory")
            return pieces
        
        # מיקומי שחמט תקינים
        piece_positions = {
            "white_king": (7, 4),
            "white_queen": (7, 3),
            "white_rook": [(7, 0), (7, 7)],
            "white_bishop": [(7, 2), (7, 5)],
            "white_knight": [(7, 1), (7, 6)],
            "white_pawn": [(6, i) for i in range(8)],
            "black_king": (0, 4),
            "black_queen": (0, 3),
            "black_rook": [(0, 0), (0, 7)],
            "black_bishop": [(0, 2), (0, 5)],
            "black_knight": [(0, 1), (0, 6)],
            "black_pawn": [(1, i) for i in range(8)],
        }
        
        # יצירת כלים
        for piece_type in available_piece_types:
            if piece_type in piece_positions:
                positions = piece_positions[piece_type]
                if isinstance(positions, tuple):
                    # כלי יחיד
                    try:
                        piece = piece_factory.create_piece(piece_type, positions)
                        pieces.append(piece)
                        print(f"Created piece: {piece.piece_id} at {positions}")
                    except Exception as e:
                        print(f"Failed to create {piece_type}: {e}")
                else:
                    # מספר כלים
                    for i, pos in enumerate(positions):
                        try:
                            piece = piece_factory.create_piece(piece_type, pos)
                            pieces.append(piece)
                            print(f"Created piece: {piece.piece_id} at {pos}")
                        except Exception as e:
                            print(f"Failed to create {piece_type}_{i+1}: {e}")
        
        print(f"Total pieces created with factory: {len(pieces)}")
        
    except Exception as e:
        print(f"Failed to use PieceFactory: {e}")
        import traceback
        traceback.print_exc()
    
    return pieces

def create_pieces(board: Board) -> list:
    """יצירת כלים למשחק"""
    
    pieces = []
    
    # קודם ננסה עם Factory אם זמין
    if PIECE_FACTORY_AVAILABLE:
        print("Trying to create pieces with PieceFactory...")
        pieces = create_pieces_with_factory(board)
    
    # אם Factory לא עבד או לא זמין, ננסה כלים פשוטים
    if not pieces:
        print("Factory failed or not available, creating simple test pieces...")
        pieces = create_simple_test_pieces(board)
    
    # הודעה אם עדיין אין כלים
    if not pieces:
        print("\n" + "="*50)
        print("ERROR: Could not create any pieces!")
        print("="*50)
        print("\nThis could be due to:")
        print("1. Missing Piece class or its dependencies")
        print("2. Missing piece definitions in 'pieces' directory")
        print("3. Import errors in required modules")
        print("\n" + "="*50)
    
    return pieces

def validate_game_components():
    """בדיקת כל הרכיבים הנדרשים למשחק"""
    
    missing_components = []
    
    # בדיקת קלסים נדרשים
    try:
        from Game import Game
    except ImportError as e:
        missing_components.append(f"Game class ({e})")
    
    try:
        from Board import Board
    except ImportError as e:
        missing_components.append(f"Board class ({e})")
    
    try:
        from img import Img
    except ImportError as e:
        missing_components.append(f"Img class ({e})")
    
    try:
        from Piece import Piece
    except ImportError as e:
        missing_components.append(f"Piece class ({e})")
    
    # בדיקת OpenCV
    try:
        import cv2
        # בדיקה בסיסית של OpenCV
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        # לא נפתח חלון כאן כי זה עלול לגרום לבעיות
    except Exception as e:
        missing_components.append(f"OpenCV ({e})")
    
    return missing_components

def main():
    """פונקציית הרצה ראשית"""
    
    print("Starting Chess Game...")
    print("=" * 40)
    
    # בדיקת רכיבים
    print("Validating game components...")
    missing = validate_game_components()
    
    if missing:
        print("\n❌ Missing components:")
        for component in missing:
            print(f"  - {component}")
        
        # בדיקה אם אפשר להמשיך בלי רכיבים מסוימים
        critical_missing = [c for c in missing if any(critical in c for critical in ["Game class", "Board class", "Img class"])]
        
        if critical_missing:
            print("\n❌ Cannot start game without these critical components.")
            return
        else:
            print("\n⚠️  Some components are missing, but we'll try to continue...")
    
    print("✅ Essential components available")
    print()
    
    # הדפסת מקשי בקרה
    print("Game Controls:")
    print("-" * 20)
    print("White Player (Player 1):")
    print("  • Arrow keys (or WASD) - Move cursor")
    print("  • Enter or Space - Select/Move piece")
    print()
    print("Black Player (Player 2):")
    print("  • IJKL keys - Move cursor")
    print("  • U key - Select/Move piece")
    print()
    print("General:")
    print("  • R - Reset selection")
    print("  • Q or ESC - Quit game")
    print()
    print("=" * 40)
    
    try:
        # יצירת הלוח
        print("Creating board...")
        board = create_board()
        print("✅ Board created successfully")
        
        # יצירת הכלים
        print("Creating pieces...")
        pieces = create_pieces(board)
        
        if not pieces:
            print("\n❌ No pieces created!")
            print("Cannot run game without pieces.")
            return
        
        print(f"✅ Created {len(pieces)} pieces")
        
        # רשימת הכלים שנוצרו
        print("\nPieces in game:")
        for i, piece in enumerate(pieces, 1):
            try:
                if hasattr(piece, 'current_state') and hasattr(piece.current_state, 'physics'):
                    row, col = piece.current_state.physics.get_cell_pos()
                    print(f"  {i}. {piece.piece_id} at ({row}, {col})")
                else:
                    print(f"  {i}. {piece.piece_id}")
            except Exception as e:
                print(f"  {i}. {piece.piece_id} (position error: {e})")
        
        # יצירת המשחק
        print("\nInitializing game...")
        game = Game(pieces, board)
        print("✅ Game initialized successfully")
        
        print("\n🎮 Starting game loop...")
        print("=" * 40)
        
        # הרצת המשחק
        game.run()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Game interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Error running game: {e}")
        print("\nFull error details:")
        import traceback
        traceback.print_exc()
        
        print("\n💡 Troubleshooting suggestions:")
        print("1. Make sure all required Python packages are installed")
        print("2. Check that all .py files are in the same directory")
        print("3. Verify OpenCV is properly installed")
        print("4. Check console output for specific error messages")
    finally:
        # ניקוי חלונות OpenCV
        try:
            cv2.destroyAllWindows()
        except:
            pass
        print("\n🏁 Game ended. Thanks for playing!")

if __name__ == "__main__":
    # בדיקה שאנחנו בתיקייה הנכונה
    current_dir = pathlib.Path.cwd()
    print(f"Running from: {current_dir}")
    
    # בדיקת קבצים נדרשים
    required_files = ["Game.py", "Board.py", "img.py"]
    existing_files = [f for f in required_files if (current_dir / f).exists()]
    missing_files = [f for f in required_files if f not in existing_files]
    
    print(f"Found files: {existing_files}")
    if missing_files:
        print(f"Missing files: {missing_files}")
        print("⚠️  Some files are missing, but we'll try to continue...")
    
    main()