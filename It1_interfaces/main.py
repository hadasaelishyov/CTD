from Game import Game
from Board import Board
from Piece import Piece
import pathlib

def create_board() -> Board:
    # לדוגמה: לוח 8x8 עם תא בגודל 100 פיקסלים
    return Board(W_cells=8, H_cells=8, cell_W_pix=100, cell_H_pix=100)

def create_pieces(board: Board) -> list[Piece]:
    # כאן את צריכה ליצור את הכלים שלך עם המיקומים ההתחלתיים
    pieces = []

    # לדוגמה, יוצרים מלך לבן ומלך שחור
    from Piece import create_king_piece  # נניח שיש לך פונקציה כזו
    pieces.append(create_king_piece("white_king", (7, 4), board))
    pieces.append(create_king_piece("black_king", (0, 4), board))

    return pieces

def main():
    board = create_board()
    pieces = create_pieces(board)
    game = Game(pieces, board)
    game.run()

if __name__ == "__main__":
    main()
