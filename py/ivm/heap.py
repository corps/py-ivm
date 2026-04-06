import dataclasses
from typing import Optional


class Wire:
    __slots__ = ('other_half', 'target')

    other_half: "Wire"
    target: "Port | None"

    def __init__(self):
        # Only used internally by make_wire_pair
        self.target = None

    def __hash__(self):
        return id(self)

    def load_target(self) -> Optional["Port"]:
        target = self.target
        if isinstance(target, Port):
            return target
        return None

    def swap_target(self, port: "Port") -> Optional["Port"]:
        old = self.load_target()
        self.target = port
        return old


def make_wire_pair() -> tuple[Wire, Wire]:
    left = Wire()
    right = Wire()
    left.other_half = right
    right.other_half = left
    return left, right


AuxPairWireReference = tuple[Wire, Wire]


class Port:
    ERASE: "NilaryNodePort"


@dataclasses.dataclass
class NilaryNodePort(Port):
    def fork(self) -> "NilaryNodePort":
        return self

    def drop(self) -> None:
        return


@dataclasses.dataclass
class ErasePort(NilaryNodePort):
    pass


Port.ERASE = ErasePort()


@dataclasses.dataclass
class WirePort(NilaryNodePort):
    wire: Wire


@dataclasses.dataclass
class BinaryNodePort(Port):
    target: Wire
    label: str

    def aux(self) -> AuxPairWireReference:
        return self.target, self.target.other_half


@dataclasses.dataclass
class CombPort(BinaryNodePort):
    label: str
    target: Wire


@dataclasses.dataclass
class BranchPort(BinaryNodePort):
    target: Wire
