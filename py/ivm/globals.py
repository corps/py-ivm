import dataclasses
from typing import Protocol, Iterator

from .extrinsics import ExtFnPort
from .heap import (
    Port,
    NilaryNodePort,
    CombPort,
    BranchPort,
    WirePort,
    make_wire_pair,
)


class ExecutionContext(Protocol):
    def link_register(self, register: int, port: Port): ...


class Instruction(Protocol):
    def execute(self, context: "ExecutionContext") -> tuple[Port, Port] | None: ...


@dataclasses.dataclass
class Nilary(Instruction):
    register0: int
    port: NilaryNodePort

    def execute(self, context: ExecutionContext) -> tuple[Port, Port] | None:
        context.link_register(self.register0, self.port.fork())
        return None


@dataclasses.dataclass
class Binary(Instruction):
    tag: str  # "Comb", "Branch", or "ExtFn"
    label: str
    register0: int
    register1: int
    register2: int

    def execute(self, context: ExecutionContext) -> tuple[Port, Port] | None:
        wire, wire_other = make_wire_pair()
        if self.tag == "Comb":
            port = CombPort(target=wire, label=self.label)
        elif self.tag == "Branch":
            port = BranchPort(target=wire, label=self.label)
        else:
            port = ExtFnPort(target=wire, label=self.label)
        context.link_register(self.register0, port)
        context.link_register(self.register1, WirePort(wire=wire))
        context.link_register(self.register2, WirePort(wire=wire_other))
        return None


@dataclasses.dataclass
class Inert(Instruction):
    register0: int
    register1: int

    def execute(self, context: ExecutionContext) -> tuple[Port, Port] | None:
        w1, w1o = make_wire_pair()
        w2, w2o = make_wire_pair()
        context.link_register(self.register0, WirePort(wire=w1))
        context.link_register(self.register1, WirePort(wire=w2))
        return WirePort(wire=w1o), WirePort(wire=w2o)


@dataclasses.dataclass
class Instructions:
    instructions: list[Instruction] = dataclasses.field(default_factory=list)
    next_register: int = 1

    def new_register(self) -> int:
        register = self.next_register
        self.next_register += 1
        return register

    def __iter__(self) -> Iterator[Instruction]:
        return iter(self.instructions)

    def append(self, instruction: Instruction) -> None:
        self.instructions.append(instruction)


@dataclasses.dataclass
class Global:
    name: str
    labels: tuple[set[str], dict[str, set[str]]] = dataclasses.field(
        default_factory=lambda: (set(), {})
    )
    instructions: Instructions = dataclasses.field(default_factory=Instructions)

    def contains_label(self, label: str) -> bool:
        s, o = self.labels
        return label in s or any(label in s_ for s_ in o.items())

    def add_label(self, label: str) -> None:
        self.labels[0].add(label)

    def extend_labels(self, other: "Global"):
        self.labels[1][other.name] = other.labels[0]


@dataclasses.dataclass
class GlobalPort(NilaryNodePort):
    global_ref: Global
