from Command import Command
from Moves import Moves
from Graphics import Graphics
from Physics import Physics
from typing import Dict
import time


class State:
    def __init__(self, moves: Moves, graphics: Graphics, physics: Physics):
        self.moves = moves
        self.graphics = graphics
        self.physics = physics
        self.transitions = {}
        self.current_command = None
        self.state_start_time = 0

    def copy(self):
        """יצירת עותק של המצב - תיקון חשוב"""
        new_moves = self.moves.copy()  # יצירת עותק של moves
        new_graphics = self.graphics.copy()
        new_physics = self.physics.copy()
        new_state = State(new_moves, new_graphics, new_physics)
        new_state.transitions = self.transitions.copy()
        new_state.current_command = self.current_command
        new_state.state_start_time = self.state_start_time
        return new_state
    
    def set_transition(self, event: str, target: "State"):
        self.transitions[event] = target

    def reset(self, cmd: Command):
        self.current_command = cmd
        self.state_start_time = cmd.timestamp
        self.graphics.reset(cmd)
        self.physics.reset(cmd)

    def can_transition(self, now_ms: int) -> bool:
        min_duration = 100
        return (now_ms - self.state_start_time) >= min_duration

    def get_state_after_command(self, cmd: Command, now_ms: int) -> "State":
        # תיקון חשוב: בדיקה אם הטרנזישן קיים
        if cmd.type not in self.transitions:
            # אם אין טרנזישן מתאים, החזר את המצב הנוכחי עם reset
            new_state = self.copy()
            new_state.reset(cmd)
            return new_state
        
        next_state = self.transitions[cmd.type].copy()  # תיקון: copy במקום שיתוף
        next_state.reset(cmd)
        return next_state

    def update(self, now_ms: int) -> "State":
        self.graphics.update(now_ms)
        self.physics.update(now_ms)
        
        # Check for automatic transitions (e.g., animation complete)
        if 'auto' in self.transitions and self.can_transition(now_ms):
            # Could add logic for automatic state transitions
            pass
            
        return self

    def get_command(self) -> Command:
        """Get the current command for this state."""
        return self.current_command