import dataclasses
from dataclasses import field
from typing import Any, Callable

from .heap import NilaryNodePort, BinaryNodePort, Wire


@dataclasses.dataclass
class ExtVal(NilaryNodePort):
    """Lightweight wrapper for external values in the interaction net."""
    value: Any

    def fork(self) -> "NilaryNodePort":
        return self

    def drop(self) -> None:
        return


# Backward compat aliases
ExtValPort = ExtVal
PrimitiveExtValPort = ExtVal


@dataclasses.dataclass
class ExtFnPort(BinaryNodePort):
    label: str
    target: Wire

    @property
    def swapped(self) -> bool:
        return self.label.endswith("$")

    def unwrap_label(self) -> str:
        if self.swapped:
            return self.label[:-1]
        else:
            return self.label

    def swap(self) -> "ExtFnPort":
        if self.swapped:
            return dataclasses.replace(self, label=self.label[:-1])
        else:
            return dataclasses.replace(self, label=self.label + "$")


@dataclasses.dataclass
class Extrinsics:
    ext_fns: dict[str, Callable] = field(default_factory=dict)
    split_ext_fns: dict[str, Callable] = field(default_factory=dict)
