
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

def create_pieces(board: Board) -> list:
    """יצירת כלים למשחק על בסיס הקבצים הקיימים"""
    
    pieces = []

    
    pieces_root = pathlib.Path("")
    
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
                           (d.name in ['BB', 'BW', 'KB', 'KW', 'NB', 'NW', 'PB', 'PW', 'QB', 'QW', 'RB', 'RW'] or
                            (d / "sprites").exists() or 
                            (d / "states").exists())]
            
            if piece_subdirs:
                pieces_dir = path
                print(f"Found pieces in: {pieces_dir}")
                break
    

    
    piece_factory = PieceFactory(board, pieces_dir)
    available_types = discover_piece_types(pieces_dir)
    
    print(f"Available piece types: {available_types}")
    
    # הגדרת מיקומים מסורתיים של שחמט
    piece_setup = {
        # שורה 1 - כלים לבנים עיקריים
        'RW': [(0, 0), (0, 7)],  # צריחים לבנים
        'NW': [(0, 1), (0, 6)],  # סוסים לבנים
        'BW': [(0, 2), (0, 5)],  # רצים לבנים
        'QW': [(0, 3)],          # מלכה לבנה
        'KW': [(0, 4)],          # מלך לבן
        
        # שורה 2 - חיילים לבנים
        'PW': [(1, col) for col in range(8)],
        
        # שורה 7 - חיילים שחורים
        'PB': [(6, col) for col in range(8)],
        
        # שורה 8 - כלים שחורים עיקריים
        'RB': [(7, 0), (7, 7)],  # צריחים שחורים
        'NB': [(7, 1), (7, 6)],  # סוסים שחורים
        'BB': [(7, 2), (7, 5)],  # רצים שחורים
        'QB': [(7, 3)],          # מלכה שחורה
        'KB': [(7, 4)],          # מלך שחור
    }
    
    # יצירת הכלים לפי ההגדרה המסורתית
    for piece_type in available_types:
        if piece_type in piece_setup:
            positions = piece_setup[piece_type]
            for row, col in positions:
                try:
                    piece = piece_factory.create_piece(piece_type, (row, col))
                    pieces.append(piece)
                    print(f"Created piece: {piece.piece_id} at ({row}, {col})")
                except Exception as e:
                    print(f"Failed to create piece {piece_type} at ({row}, {col}): {e}")
    
    # אם לא הצלחנו ליצור כלים, ננסה ליצור כמה כלים בסיסיים לפחות
    if not pieces:
        print("Failed to create standard setup, trying basic pieces...")
        basic_setup = [
            ('KW', (0, 4)), ('KB', (7, 4)),  # מלכים
            ('QW', (0, 3)), ('QB', (7, 3)),  # מלכות
            ('RW', (0, 0)), ('RB', (7, 0)),  # צריחים
            ('BW', (0, 2)), ('BB', (7, 2)),  # רצים
        ]
        
        for piece_type, (row, col) in basic_setup:
            if piece_type in available_types:
                try:
                    piece = piece_factory.create_piece(piece_type, (row, col))
                    pieces.append(piece)
                    print(f"Created basic piece: {piece.piece_id} at ({row}, {col})")
                except Exception as e:
                    print(f"Failed to create basic piece {piece_type}: {e}")
    

    
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

    
    try:
        # יצירת הלוח
        print("\n🏁 Creating board...")
        board = create_board()

        
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
        
        
    finally:
        try:
            cv2.destroyAllWindows()
        except:
            pass
        
        print("\n🏁 Game session ended. Thanks for playing!")


if __name__ == "__main__":
    main()