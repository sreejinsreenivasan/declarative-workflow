from __future__ import annotations

from typing import Callable


class Registry:
    def __init__(self) -> None:
        self._nodes: dict[str, type] = {}

    def register(self, type_name: str) -> Callable[[type], type]:
        def decorator(cls: type) -> type:
            if type_name in self._nodes:
                raise ValueError(f"'{type_name}' already registered")
            self._nodes[type_name] = cls
            return cls

        return decorator

    def resolve(self, type_name: str) -> type:
        if type_name not in self._nodes:
            raise KeyError(f"node type '{type_name}' not registered")
        return self._nodes[type_name]

    def __contains__(self, type_name: str) -> bool:
        return type_name in self._nodes
