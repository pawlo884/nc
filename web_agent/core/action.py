"""
Klasa Action - reprezentuje pojedynczą akcję do wykonania
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Typy akcji które agent może wykonać"""
    NAVIGATE = 'navigate'
    CLICK = 'click'
    FILL = 'fill'
    WAIT_FOR = 'wait_for'
    WAIT = 'wait'
    EVALUATE = 'evaluate'
    SCREENSHOT = 'screenshot'
    GET_TEXT = 'get_text'


@dataclass
class ActionResult:
    """Wynik wykonania akcji"""
    success: bool
    action_type: ActionType
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje wynik do słownika"""
        return {
            'success': self.success,
            'action_type': self.action_type.value,
            'data': self.data,
            'error': self.error,
            'timestamp': self.timestamp
        }


class Action:
    """
    Reprezentuje pojedynczą akcję do wykonania przez agenta.
    Każda akcja ma typ, parametry i opcjonalne warunki.
    """
    
    def __init__(
        self,
        action_type: ActionType,
        **params
    ):
        """
        Args:
            action_type: Typ akcji
            **params: Parametry akcji (zależą od typu)
        """
        self.action_type = action_type
        self.params = params
        self.optional = params.get('optional', False)
        self.retry_count = params.get('retry_count', 0)
        self.timeout = params.get('timeout', 10000)
        
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje akcję do słownika (dla zapisu w bazie)"""
        return {
            'type': self.action_type.value,
            **self.params
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Tworzy akcję ze słownika"""
        action_type = ActionType(data['type'])
        params = {k: v for k, v in data.items() if k != 'type'}
        return cls(action_type, **params)
    
    def __repr__(self):
        return f"Action(type={self.action_type.value}, params={self.params})"

