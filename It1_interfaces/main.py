
import pathlib
import cv2
import numpy as np
import sys
import os
import time

# נוסיף try-except לכל הייבואים
try:
    from Game import Game
except ImportError as e:
    print(f"Error importing Game: {e}")
    Game = None

try:
    from Board import Board
except ImportError as e:
    print(f"Error importing Board: {e}")
    Board = None

try:
    from img import Img
except ImportError as e:
    print(f"Error importing Img: {e}")
    # נייצר מחלקת Img פשוטה אם לא קיימת
    class Img:
        def __init__(self):
            self.img = None
        
        def put_text(self, text, x, y, scale, color, thickness):
            if self.img is not None:
                cv2.putText(self.img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 
                           scale, color[:3], thickness)

try:
    from PieceFactory import PieceFactory
except ImportError as e:
    print(f"Error importing PieceFactory: {e}")
    PieceFactory = None

try:
    from Piece import Piece
except ImportError as e:
    print(f"Error importing Piece: {e}")
    Piece = None


def create_minimal_img_class():
    """יצירת מחלקת Img מינימלית אם לא קיימת"""
    class MinimalImg:
        def __init__(self):
            self.img = None
        
        def put_text(self, text, x, y, scale, color, thickness):
            if self.img is not None:
                cv2.putText(self.img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 
                           scale, color[:3], thickness)
    
    return MinimalImg


def create_board() -> Board:
    """יצירת לוח שחמט 8x8 עם תאים בגודל 80x80 פיקסלים"""
    
    if Board is None:
        print("Board class not available!")
        return None
    
    # יצירת תמונה בסיסית ללוח
    cell_size = 80
    board_width = 8 * cell_size
    board_height = 8 * cell_size
    
    # יצירת תמונת לוח שחמט עם צבעים לסירוגין
    board_img = np.zeros((board_height, board_width, 3), dtype=np.uint8)  # שינוי ל-3 ערוצים
    
    # צבעים משופרים ללוח שחמט
    light_color = [240, 217, 181]  # בז' בהיר (בלי אלפא)
    dark_color = [181, 136, 99]    # חום (בלי אלפא)
    
    for row in range(8):
        for col in range(8):
            color = light_color if (row + col) % 2 == 0 else dark_color
            y_start = row * cell_size
            y_end = (row + 1) * cell_size
            x_start = col * cell_size
            x_end = (col + 1) * cell_size
            
            board_img[y_start:y_end, x_start:x_end] = color
    
    # הוספת מספרי שורות ואותיות עמודות
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    text_color = (60, 60, 60)  # אפור כהה (בלי אלפא)
    
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
    if Img:
        img_obj = Img()
    else:
        img_obj = create_minimal_img_class()()
    
    img_obj.img = board_img
    
    return Board(
        cell_W_pix=cell_size,
        cell_H_pix=cell_size,
        W_cells=8,
        H_cells=8,
        img=img_obj
    )


def create_demo_pieces():
    """יצירת כלים פשוטים לדמו (אם אין PieceFactory)"""
    
    if not (Piece and Board):
        print("Missing required classes for pieces")
        return []
    
    pieces = []
    
    # ננסה ליצור כמה כלים פשוטים
    try:
        # יצירת מחלקות פשוטות לדמו
        class DemoState:
            def __init__(self, row, col):
                self.physics = DemoPhysics(row, col)
                self.graphics = DemoGraphics()
                self.current_command = None
            
            def get_state_after_command(self, cmd, now_ms):
                return self
            
            def update(self, now_ms):
                return self
            
            def reset(self, cmd):
                pass
        
        class DemoPhysics:
            def __init__(self, row, col):
                self.row = row
                self.col = col
                self.cooldown_start_ms = 0
                self.cooldown_duration_ms = 1000
            
            def get_cell_pos(self):
                return (self.row, self.col)
            
            def get_pos(self):
                return (self.row, self.col)
            
            def can_capture(self, now_ms):
                return True
            
            def can_be_captured(self, now_ms):
                return True
        
        class DemoGraphics:
            def __init__(self):
                pass
            
            def get_img(self):
                return DemoSprite()
        
        class DemoSprite:
            def draw_on(self, target_img, x, y):
                # ציור ריבוע פשוט
                cv2.rectangle(target_img.img, (x+10, y+10), (x+70, y+70), (255, 0, 0), -1)
        
        # יצירת כמה כלים לדמו
        demo_positions = [(0, 0), (0, 7), (7, 0), (7, 7)]
        
        for i, (row, col) in enumerate(demo_positions):
            state = DemoState(row, col)
            piece = Piece(f"demo_piece_{i+1}", state)
            pieces.append(piece)
            print(f"Created demo piece at ({row}, {col})")
    
    except Exception as e:
        print(f"Error creating demo pieces: {e}")
    
    return pieces


def create_pieces(board: Board) -> list:
    """יצירת כלים למשחק על בסיס הקבצים הקיימים"""
    
    pieces = []
    
    if PieceFactory is None:
        print("PieceFactory not available, creating demo pieces...")
        return create_demo_pieces()
    
    pieces_root = pathlib.Path(".")
    
    # חיפוש תיקיית pieces
    possible_paths = [
        pathlib.Path("pieces"),
        pathlib.Path("."),
        pathlib.Path("It1_interfaces"),
        pathlib.Path("../pieces")
    ]
    
    pieces_dir = None
    for path in possible_paths:
        if path.exists():
            piece_subdirs = [d for d in path.iterdir() 
                           if d.is_dir() and 
                           (d.name in ['BB', 'BW', 'king', 'queen', 'pawn', 'rook', 'knight', 'bishop'] or
                            (d / "sprites").exists() or 
                            (d / "states").exists())]
            
            if piece_subdirs:
                pieces_dir = path
                print(f"Found pieces in: {pieces_dir}")
                break
    
    if not pieces_dir:
        print("No pieces directory found, creating demo pieces...")
        return create_demo_pieces()
    
    try:
        piece_factory = PieceFactory(board, pieces_dir)
        available_types = discover_piece_types(pieces_dir)
        
        if not available_types:
            print("No valid piece types found, creating demo pieces...")
            return create_demo_pieces()
        
        print(f"Available piece types: {available_types}")
        
        # יצירת כמה כלים פשוטים לבדיקה
        test_positions = [(3, 3), (4, 4)]
        
        for i, (row, col) in enumerate(test_positions):
            if i < len(available_types):
                piece_type = available_types[i]
                try:
                    piece = piece_factory.create_piece(piece_type, (row, col))
                    pieces.append(piece)
                    print(f"Created piece: {piece.piece_id} at ({row}, {col})")
                except Exception as e:
                    print(f"Failed to create piece {piece_type}: {e}")
        
        if not pieces:
            print("Failed to create any pieces with PieceFactory, using demo...")
            return create_demo_pieces()
        
    except Exception as e:
        print(f"Error with PieceFactory: {e}")
        return create_demo_pieces()
    
    return pieces


def discover_piece_types(pieces_root: pathlib.Path) -> list:
    """גילוי סוגי הכלים הקיימים בתיקיית pieces"""
    
    if not pieces_root.exists():
        return []
    
    piece_types = []
    
    try:
        for piece_dir in pieces_root.iterdir():
            if piece_dir.is_dir():
                has_sprites = (piece_dir / "sprites").exists()
                has_states = (piece_dir / "states").exists()
                
                if has_sprites or has_states:
                    piece_types.append(piece_dir.name)
    except Exception as e:
        print(f"Error discovering pieces: {e}")
    
    return piece_types


def validate_game_setup():
    """בדיקת תקינות הסטאפ"""
    
    issues = []
    
    # בדיקת OpenCV
    try:
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imshow("test", test_img)
        cv2.waitKey(1)
        cv2.destroyAllWindows()
    except Exception as e:
        issues.append(f"OpenCV issue: {e}")
    
    if Game is None:
        issues.append("Game class not available")
    
    if Board is None:
        issues.append("Board class not available")
    
    return issues


def create_simple_demo():
    """יצירת דמו פשוט אם כל השאר נכשל"""
    
    print("Creating simple demo...")
    
    # יצירת לוח פשוט
    cell_size = 80
    board_width = 8 * cell_size
    board_height = 8 * cell_size
    
    board_img = np.zeros((board_height, board_width, 3), dtype=np.uint8)
    
    # צבעים לסירוגין
    light_color = [240, 217, 181]
    dark_color = [181, 136, 99]
    
    for row in range(8):
        for col in range(8):
            color = light_color if (row + col) % 2 == 0 else dark_color
            y_start = row * cell_size
            y_end = (row + 1) * cell_size
            x_start = col * cell_size
            x_end = (col + 1) * cell_size
            
            board_img[y_start:y_end, x_start:x_end] = color
    
    # הוספת כמה ריבועים צבעוניים כ"כלים"
    piece_positions = [(100, 100), (180, 180), (340, 340), (420, 420)]
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    
    for (x, y), color in zip(piece_positions, colors):
        cv2.rectangle(board_img, (x, y), (x+60, y+60), color, -1)
        cv2.rectangle(board_img, (x, y), (x+60, y+60), (0, 0, 0), 2)
    
    # הצגת הדמו
    window_name = "Simple Chess Demo"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    
    print("Demo created! Press any key to close or 'q' to quit")
    
    try:
        while True:
            cv2.imshow(window_name, board_img)
            key = cv2.waitKey(30) & 0xFF
            
            if key == ord('q') or key == 27:  # q או ESC
                break
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
    
    except Exception as e:
        print(f"Error in demo loop: {e}")
    
    finally:
        cv2.destroyAllWindows()


def main():
    """פונקציית הרצה ראשית"""
    
    print("🚀 Starting Chess Game...")
    print(f"📁 Working directory: {pathlib.Path.cwd()}")
    
    # בדיקת הסטאפ
    print("\n🔍 Validating setup...")
    issues = validate_game_setup()
    
    if issues:
        print("\n⚠️  Setup issues found:")
        for issue in issues:
            print(f"   • {issue}")
    
    # אם יש בעיות קריטיות, נריץ דמו פשוט
    if Game is None or Board is None:
        print("\n⚠️  Missing critical classes. Running simple demo instead...")
        create_simple_demo()
        return
    
    try:
        # יצירת הלוח
        print("\n🏁 Creating board...")
        board = create_board()
        
        if board is None:
            print("Failed to create board, running simple demo...")
            create_simple_demo()
            return
        
        print("✅ Board created successfully")
        
        # יצירת הכלים
        print("\n♟️  Creating pieces...")
        pieces = create_pieces(board)
        
        print(f"✅ Created {len(pieces)} pieces successfully")
        
        # הדפסת פרטי הכלים
        if pieces:
            print(f"\n📋 Pieces created:")
            for i, piece in enumerate(pieces, 1):
                print(f"   {i:2}. {piece.piece_id}")
        
        # יצירת המשחק
        print(f"\n🎮 Initializing game...")
        game = Game(pieces, board)
        print("✅ Game initialized successfully")
        
        print("\n🎯 Controls:")
        print("   • Arrow Keys / WASD - Move cursor")
        print("   • Enter/Space - Select piece")
        print("   • Q/ESC - Quit game")
        
        input("\nPress ENTER to start the game...")
        
        # הרצת המשחק
        print("\n🎯 Starting game loop...")
        game.run()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Game interrupted by user (Ctrl+C)")
        
    except Exception as e:
        print(f"\n❌ Error during game execution:")
        print(f"   {type(e).__name__}: {e}")
        
        print(f"\n🔧 Running simple demo instead...")
        create_simple_demo()
        
    finally:
        try:
            cv2.destroyAllWindows()
        except:
            pass
        
        print("\n🏁 Game session ended. Thanks for playing!")


if __name__ == "__main__":
    main()