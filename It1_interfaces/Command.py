from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

@dataclass
class Command:
    timestamp: int          # ms since game start
    piece_id: str
    type: str               # "Move" | "Jump" | …
    params: List            # payload (e.g. ["e2", "e4"]) 

def is_movement_command(self) -> bool:
    """בדיקה האם זו פקודת תנועה"""
    return self.type in ["Move", "Jump"]

def get_priority_timestamp(self) -> int:
    """קבלת זמן לצורך קביעת עדיפות"""
    return self.timestamp