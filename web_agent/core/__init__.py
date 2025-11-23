"""
Core module - podstawowe klasy i interfejsy dla agenta web
"""

from .browser import Browser
from .action import Action, ActionResult, ActionType
from .workflow import Workflow, WorkflowStep

__all__ = ['Browser', 'Action', 'ActionResult', 'ActionType', 'Workflow', 'WorkflowStep']

