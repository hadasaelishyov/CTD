import pathlib
import cv2
import numpy as np
from Game import Game
from Board import Board
from PieceFactory import PieceFactory
from img import Img

def create_board() -> Board:
    """יצירת לוח שחמט 8x8 עם תאים בגודל 64x64 פיקסלים"""
    
    # יצירת תמונה בסיסית ללוח
    cell_size = 64
    board_width = 8 * cell_size
    board_height = 8 * cell_size
    
    # יצירת תמונת לוח שחמט עם צבעים לסירוגין
    board_img = np.zeros((board_height, board_width, 4), dtype=np.uint8)
    
    # צביעת הלוח בצבעים לסירוגין (חום בהיר/כהה)
    light_color = [240, 217, 181, 255]  # חום בהיר
    dark_color = [181, 136, 99, 255]    # חום כהה
    
    for row in range(8):
        for col in range(8):
            color = light_color if (row + col) % 2 == 0 else dark_color
            y_start = row * cell_size
            y_end = (row + 1) * cell_size
            x_start = col * cell_size
            x_end = (col + 1) * cell_size
            
            board_img[y_start:y_end, x_start:x_end] = color
    
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

def create_pieces(board: Board) -> list:
    """יצירת כלים למשחק בהתבסס על התיקיות שקיימות"""
    
    pieces = []
    pieces_root = pathlib.Path("pieces")
    
    if not pieces_root.exists():
        print(f"Warning: pieces directory not found at {pieces_root}")
        return pieces
    
    # יצירת factory לכלים
    piece_factory = PieceFactory(board, pieces_root)
    
    # בדיקה אילו סוגי כלים קיימים
    available_piece_types = []
    for piece_dir in pieces_root.iterdir():
        if piece_dir.is_dir():
            available_piece_types.append(piece_dir.name)
    
    print(f"Available piece types: {available_piece_types}")
    
    # מיקום התחלתי לכלים - נסה ליצור כלים בהתבסס על מה שקיים
    piece_positions = {
        # שורה אחורית לבן (row 7)
        'R': [(7, 0), (7, 7)],  # צריחים
        'N': [(7, 1), (7, 6)],  # פרשים
        'B': [(7, 2), (7, 5)],  # רצים
        'Q': [(7, 3)],          # מלכה
        'K': [(7, 4)],          # מלך
        'P': [(6, i) for i in range(8)],  # חיילים
        
        # שורה אחורית שחור (row 0)
        'r': [(0, 0), (0, 7)],  # צריחים
        'n': [(0, 1), (0, 6)],  # פרשים
        'b': [(0, 2), (0, 5)],  # רצים
        'q': [(0, 3)],          # מלכה
        'k': [(0, 4)],          # מלך
        'p': [(1, i) for i in range(8)],  # חיילים
    }
    
    # ניסיון ליצירת כלים
    piece_count = 0
    
    for piece_type in available_piece_types:
        # ניסיון למיפוי שם התיקייה לסוג כלי
        mapped_type = None
        piece_type_lower = piece_type.lower()
        
        # מיפוי אפשרי של שמות לסוגי כלים
        if 'king' in piece_type_lower or piece_type.upper() in ['K', 'k']:
            mapped_type = 'K' if 'w' in piece_type_lower or 'white' in piece_type_lower else 'k'
        elif 'queen' in piece_type_lower or piece_type.upper() in ['Q', 'q']:
            mapped_type = 'Q' if 'w' in piece_type_lower or 'white' in piece_type_lower else 'q'
        elif 'rook' in piece_type_lower or piece_type.upper() in ['R', 'r']:
            mapped_type = 'R' if 'w' in piece_type_lower or 'white' in piece_type_lower else 'r'
        elif 'bishop' in piece_type_lower or piece_type.upper() in ['B', 'b']:
            mapped_type = 'B' if 'w' in piece_type_lower or 'white' in piece_type_lower else 'b'
        elif 'knight' in piece_type_lower or piece_type.upper() in ['N', 'n']:
            mapped_type = 'N' if 'w' in piece_type_lower or 'white' in piece_type_lower else 'n'
        elif 'pawn' in piece_type_lower or piece_type.upper() in ['P', 'p']:
            mapped_type = 'P' if 'w' in piece_type_lower or 'white' in piece_type_lower else 'p'
        
        # אם לא הצלחנו למפות, נצור בכל זאת כלי במיקום ברירת מחדל
        if mapped_type and mapped_type in piece_positions:
            positions = piece_positions[mapped_type]
        else:
            # מיקום ברירת מחדל
            positions = [(piece_count % 8, piece_count // 8)]
        
        # יצירת כלי לכל מיקום
        for position in positions:
            try:
                piece = piece_factory.create_piece(piece_type, position)
                pieces.append(piece)
                piece_count += 1
                print(f"Created piece: {piece.piece_id} at position {position}")
                
                # הגבלת מספר הכלים למניעת עומס
                if piece_count >= 16:  # מקסימום 16 כלים
                    break
            except Exception as e:
                print(f"Failed to create piece {piece_type} at {position}: {e}")
        
        if piece_count >= 16:
            break
    
    # אם לא הצלחנו ליצור כלים מהתיקיות, ננסה ליצור כלים בסיסיים
    if not pieces:
        print("No pieces created from directories, creating basic test pieces...")
        
        # ניסיון ליצור כלים בסיסיים אם יש לפחות תיקייה אחת
        if available_piece_types:
            test_positions = [(0, 0), (0, 7), (7, 0), (7, 7)]  # פינות הלוח
            
            for i, pos in enumerate(test_positions):
                if i < len(available_piece_types):
                    try:
                        piece = piece_factory.create_piece(available_piece_types[i], pos)
                        pieces.append(piece)
                        print(f"Created test piece: {piece.piece_id} at {pos}")
                    except Exception as e:
                        print(f"Failed to create test piece: {e}")
    
    print(f"Total pieces created: {len(pieces)}")
    return pieces

def main():
    """פונקציית הרצה ראשית"""
    
    print("Starting Chess Game...")
    print("Controls:")
    print("Player 1: Arrow keys to move cursor, Enter to select/move")
    print("Player 2: WASD to move cursor, Space to select/move")
    print("Press 'q' or ESC to quit")
    print()
    
    try:
        # יצירת הלוח
        print("Creating board...")
        board = create_board()
        
        # יצירת הכלים
        print("Creating pieces...")
        pieces = create_pieces(board)
        
        if not pieces:
            print("No pieces created! Check your 'pieces' directory structure.")
            print("Expected structure:")
            print("pieces/")
            print("  ├── piece_name1/")
            print("  │   ├── config.json (optional)")
            print("  │   ├── moves.txt")
            print("  │   └── states/")
            print("  │       └── idle/")
            print("  │           └── sprites/")
            print("  │               ├── 1.png")
            print("  │               └── ...")
            print("  └── piece_name2/")
            print("      └── ...")
            return
        
        # יצירת המשחק
        print("Initializing game...")
        game = Game(pieces, board)
        
        print("Game started! Enjoy!")
        print("=" * 40)
        
        # הרצת המשחק
        game.run()
        
    except KeyboardInterrupt:
        print("\nGame interrupted by user")
    except Exception as e:
        print(f"Error running game: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # ניקוי חלונות OpenCV
        cv2.destroyAllWindows()
        print("Game ended.")

if __name__ == "__main__":
    main()