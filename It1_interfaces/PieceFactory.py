import pathlib
from typing import Dict, Tuple
import json
from Board import Board
from GraphicsFactory import GraphicsFactory
from Moves import Moves
from PhysicsFactory import PhysicsFactory
from Piece import Piece
from State import State


class PieceFactory:
    def __init__(self, board: Board, pieces_root: pathlib.Path):
        self.board = board
        self.pieces_root = pieces_root
        self.graphics_factory = GraphicsFactory()
        self.physics_factory = PhysicsFactory(board)
        self.piece_templates = {}
        self._load_piece_templates()

    def _load_piece_templates(self):
        """Load all piece templates from the pieces directory."""
        if not self.pieces_root.exists():
            print(f"Pieces directory not found: {self.pieces_root}")
            return

        for piece_dir in self.pieces_root.iterdir():
            if piece_dir.is_dir():
                try:
                    state_machine = self._build_state_machine(piece_dir)
                    self.piece_templates[piece_dir.name] = state_machine
                    print(f"Loaded piece template: {piece_dir.name}")
                except Exception as e:
                    print(f"Failed to load piece template {piece_dir.name}: {e}")
                        
    def _build_state_machine(self, piece_dir: pathlib.Path) -> State:
        config_file = piece_dir / "config.json"
        config = {}
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                print(f"Failed to load config for {piece_dir.name}: {e}")

        # Create cell size from board
        cell_size = (self.board.cell_W_pix, self.board.cell_H_pix)

        # Create components for idle state (default state)
        moves_file = piece_dir / "moves.txt"
        if not moves_file.exists():
            # Create default moves file with safe default
            moves_file.parent.mkdir(parents=True, exist_ok=True)
            with open(moves_file, 'w', encoding='utf-8') as f:
                f.write("# Default moves - one step in each direction\n")
                f.write("0,1\n")   # up
                f.write("0,-1\n")  # down  
                f.write("1,0\n")   # right
                f.write("-1,0\n")  # left
                f.write("1,1\n")   # up-right
                f.write("1,-1\n")  # down-right
                f.write("-1,1\n")  # up-left
                f.write("-1,-1\n") # down-left
        
        moves = Moves(moves_file, (self.board.H_cells, self.board.W_cells))  # תיקון: H,W
        
        # Load graphics from states directory
        states_dir = piece_dir / "states"
        sprites_dir = None
        
        if states_dir.exists():
            # Try to load idle state first
            idle_sprites_dir = states_dir / "idle" / "sprites"
            if idle_sprites_dir.exists():
                sprites_dir = idle_sprites_dir
            else:
                # Fallback to first available state
                for state_subdir in states_dir.iterdir():
                    candidate_sprites_dir = state_subdir / "sprites"
                    if candidate_sprites_dir.exists():
                        sprites_dir = candidate_sprites_dir
                        break
        
        # Final fallback
        if sprites_dir is None:
            sprites_dir = piece_dir / "sprites"
            if not sprites_dir.exists():
                sprites_dir = piece_dir  # Use piece root as last resort

        graphics = self.graphics_factory.load(sprites_dir, config.get('graphics', {}), cell_size)
        physics = self.physics_factory.create((0, 0), config.get('physics', {}))
        
        # Create the idle state
        idle_state = State(moves, graphics, physics)
        
        # TODO: Add more states (move, jump, capture) and transitions
        # For now, just return the idle state
        
        return idle_state

    def create_piece(self, p_type: str, cell: Tuple[int, int]) -> Piece:
        """יצירת כלי חדש מסוג מסוים"""
        if p_type not in self.piece_templates:
            available_types = list(self.piece_templates.keys())
            raise ValueError(f"Unknown piece type: {p_type}. Available types: {available_types}")
        
        # Clone the template state
        template_state = self.piece_templates[p_type]
        
        # תיקון חשוב: יצירת עותק מלא של המצב
        new_state = template_state.copy()
        
        # הגדרת מיקום התחלתי
        new_state.physics.set_position(cell)
        
        # Generate unique piece ID
        import uuid
        piece_id = f"{p_type}_{uuid.uuid4().hex[:8]}"
        
        return Piece(piece_id, new_state)