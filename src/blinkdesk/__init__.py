"""Lightweight ticketing system using SQLite with no external dependencies."""

__version__ = "0.7.0"

from blinkdesk.comment import Comment
from blinkdesk.category import Category
from blinkdesk.entity import Entity
from blinkdesk.init import init_db
from blinkdesk.priority import TicketPriority, TicketPriorityManager
from blinkdesk.state import TicketState, TicketStateMachine
from blinkdesk.system import TicketingSystem
from blinkdesk.ticket import Ticket
from blinkdesk.ticket_log import TicketLog, TicketLogAction

__all__ = [
    "TicketingSystem",
    "Ticket",
    "Entity",
    "TicketState",
    "TicketStateMachine",
    "TicketPriority",
    "TicketPriorityManager",
    "TicketLog",
    "TicketLogAction",
    "Comment",
    "Category",
    "init_db",
]
