from typing import List, Dict
from dataclasses import dataclass
from threading import Lock

from .groupme_message import Message
from .handlers import MessageHandler, CommandHandler


@dataclass
class Route:
    name: str
    handler: MessageHandler
    executions: int = 0

# TODO: Unify with bots Singleton
class SingletonMeta(type):
    """
    A thread-safe implementation of Singleton.
    """

    _instances = {}
    _lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            return cls._instances[cls]


class MessageRouter(metaclass=SingletonMeta):
    '''Routes messages to appropriate handlers.'''

    _routes: Dict[str, Route]

    def __init__(self, handlers: List[MessageHandler]) -> None:
        self._routes = {
            handler.__name__: Route(handler.__name__, handler) for handler in handlers
        }

    @property
    def get_routes(self) -> List[Route]:
        return self._routes

    def get_route_by_name(self, name: str):
        return self._routes.get(name)

    def route(self, message: Message) -> dict:
        '''Routes message to all applicable handlers.'''
        for route in self._routes.values():
            if route.handler.can_handle(message):
                result = route.handler.execute(message)
                route.executions += 1
                return result
