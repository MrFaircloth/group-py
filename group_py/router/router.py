from typing import List, Dict
from dataclasses import dataclass

from .groupme_message import Message
from .handlers import MessageHandler


@dataclass
class Route:
    name: str
    handler: MessageHandler
    executions: int = 0


class MessageRouter:
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
