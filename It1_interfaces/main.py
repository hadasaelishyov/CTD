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

# Import עם טיפול בשגיאות עבור Piece
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

def create_simple_test_pieces(board: Board) -> list:
    """יצירת כלים פשוטים לבדיקה אם PieceFactory לא זמין"""
    
    pieces = []
    
    if not PIECE_CLASS_AVAILABLE:
        print("Error: Cannot create pieces without Piece class")
        return pieces
    
    # נסה ליצור כלים פשוטים
    try:
        # כלי לבן פשוט
        from Piece import Piece
        from Physics import Physics
        from State import State
        
        # יצירת כלי פשוט - לבן
        white_piece_physics = Physics(board, 7, 0)  # פינה שמאל למטה
        white_piece_state = State(white_piece_physics, None)
        white_piece = Piece("white_test_piece", [white_piece_state])
        pieces.append(white_piece)
        
        # יצירת כלי פשוט - שחור  
        black_piece_physics = Physics(board, 0, 7)  # פינה ימין למעלה
        black_piece_state = State(black_piece_physics, None)
        black_piece = Piece("black_test_piece", [black_piece_state])
        pieces.append(black_piece)
        
        print("Created 2 simple test pieces")
        
    except Exception as e:
        print(f"Failed to create simple test pieces: {e}")
    
    return pieces

def create_pieces_with_factory(board: Board) -> list:
    """יצירת כלים באמצעות PieceFactory"""
    
    pieces = []
    pieces_root = pathlib.Path("pieces")
    
    if not pieces_root.exists():
        print(f"Pieces directory not found at {pieces_root}")
        print("Creating pieces directory structure...")
        try:
            pieces_root.mkdir(exist_ok=True)
            print(f"Created {pieces_root} directory")
            print("Please add piece definitions to this directory")
        except Exception as e:
            print(f"Failed to create pieces directory: {e}")
        return pieces
    
    # יצירת factory לכלים
    try:
        piece_factory = PieceFactory(board, pieces_root)
    except Exception as e:
        print(f"Failed to create PieceFactory: {e}")
        return pieces
    
    # בדיקה אילו סוגי כלים קיימים
    available_piece_types = []
    for piece_dir in pieces_root.iterdir():
        if piece_dir.is_dir():
            available_piece_types.append(piece_dir.name)
    
    print(f"Available piece types: {available_piece_types}")
    
    if not available_piece_types:
        print("No piece types found in pieces directory")
        return pieces
    
    # מיקומים פשוטים לבדיקה
    test_positions = [
        (0, 0), (0, 7),  # פינות עליונות
        (7, 0), (7, 7),  # פינות תחתונות
        (3, 3), (3, 4),  # מרכז
        (4, 3), (4, 4)   # מרכז
    ]
    
    # יצירת כלים
    piece_count = 0
    for i, piece_type in enumerate(available_piece_types):
        if i >= len(test_positions):
            break
            
        position = test_positions[i]
        
        try:
            piece = piece_factory.create_piece(piece_type, position)
            pieces.append(piece)
            piece_count += 1
            print(f"Created piece: {piece.piece_id} at position {position}")
            
        except Exception as e:
            print(f"Failed to create piece {piece_type} at {position}: {e}")
    
    print(f"Total pieces created with factory: {len(pieces)}")
    return pieces

def create_pieces(board: Board) -> list:
    """יצירת כלים למשחק"""
    
    pieces = []
    
    # ניסיון ליצור כלים עם Factory
    if PIECE_FACTORY_AVAILABLE:
        print("Trying to create pieces with PieceFactory...")
        pieces = create_pieces_with_factory(board)
    
    # אם לא הצלחנו, ננסה כלים פשוטים
    if not pieces:
        print("Factory failed or not available, trying simple test pieces...")
        pieces = create_simple_test_pieces(board)
    
    # אם עדיין לא הצלחנו - הודעת שגיאה מפורטת
    if not pieces:
        print("\n" + "="*50)
        print("ERROR: Could not create any pieces!")
        print("="*50)
        print("\nTo fix this, you need:")
        print("1. A 'pieces' directory with piece definitions")
        print("2. Working PieceFactory class")
        print("3. Working Piece class with proper imports")
        print("\nExpected directory structure:")
        print("pieces/")
        print("  ├── white_king/")
        print("  │   ├── moves.txt")
        print("  │   └── states/")
        print("  │       └── idle/")
        print("  │           └── sprites/")
        print("  │               └── 1.png")
        print("  └── black_king/")
        print("      └── ...")
        print("\n" + "="*50)
    
    return pieces

def validate_game_components():
    """בדיקת כל הרכיבים הנדרשים למשחק"""
    
    missing_components = []
    
    # בדיקת קלסים נדרשים
    try:
        from Game import Game
    except ImportError:
        missing_components.append("Game class")
    
    try:
        from Board import Board
    except ImportError:
        missing_components.append("Board class")
    
    try:
        from img import Img
    except ImportError:
        missing_components.append("Img class")
    
    # בדיקת OpenCV
    try:
        import cv2
        # בדיקה בסיסית של OpenCV
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imshow("test", test_img)
        cv2.destroyAllWindows()
    except Exception as e:
        missing_components.append(f"OpenCV (error: {e})")
    
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
        print("\nCannot start game without these components.")
        return
    
    print("✅ All basic components available")
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
            print("The game needs at least 2 pieces to run.")
            print("Please check your piece definitions and try again.")
            return
        
        print(f"✅ Created {len(pieces)} pieces")
        
        # רשימת הכלים שנוצרו
        print("\nPieces in game:")
        for i, piece in enumerate(pieces, 1):
            print(f"  {i}. {piece.piece_id}")
        
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
        print("\n💡 Try running with simpler piece configurations")
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
    missing_files = [f for f in required_files if not (current_dir / f).exists()]
    
    if missing_files:
        print(f"\n❌ Missing required files: {missing_files}")
        print("Make sure you're running from the correct directory")
        sys.exit(1)
    
    main()