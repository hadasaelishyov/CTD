
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
            # Create default moves file
            with open(moves_file, 'w') as f:
                f.write("default=all_directions\n")
        
        moves = Moves(moves_file, (self.board.W_cells, self.board.H_cells))
        
        # Load graphics from states directory
        states_dir = piece_dir / "states"
        if states_dir.exists():
            # Try to load idle state first
            idle_sprites_dir = states_dir / "idle" / "sprites"
            if not idle_sprites_dir.exists():
                # Fallback to first available state
                for state_subdir in states_dir.iterdir():
                    sprites_dir = state_subdir / "sprites"
                    if sprites_dir.exists():
                        idle_sprites_dir = sprites_dir
                        break
        else:
            idle_sprites_dir = piece_dir  # Fallback to piece root

        graphics = self.graphics_factory.load(idle_sprites_dir, config.get('graphics', {}), cell_size)
        physics = self.physics_factory.create((0, 0), config.get('physics', {}))
        
        # Create the idle state
        idle_state = State(moves, graphics, physics)
        
        # TODO: Add more states (move, jump, capture) and transitions
        # For now, just return the idle state
        
        return idle_state

    def create_piece(self, p_type: str, cell: Tuple[int, int]) -> Piece:
        if p_type not in self.piece_templates:
            raise ValueError(f"Unknown piece type: {p_type}")
        
        # Clone the template state
        template_state = self.piece_templates[p_type]
        
        # Create new components for this piece instance
        cell_size = (self.board.cell_W_pix, self.board.cell_H_pix)
        
        new_graphics = template_state.graphics.copy()
        new_physics = self.physics_factory.create(cell, {})
        new_moves = template_state.moves  # Can be shared
        
        new_state = State(new_moves, new_graphics, new_physics)
        
        # Generate unique piece ID
        import uuid
        piece_id = f"{p_type}_{uuid.uuid4().hex[:8]}"
        
        return Piece(piece_id, new_state)
