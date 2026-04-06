import dataclasses
from dataclasses import field
from typing import TypeVar, Iterable, Iterator, Generator

from .heap import (
    Port,
    Wire,
    WirePort,
    CombPort,
    ErasePort,
    BranchPort,
    NilaryNodePort,
    BinaryNodePort,
    make_wire_pair,
)
from .globals import Global, GlobalPort, Instructions, ExecutionContext
from .extrinsics import ExtVal, ExtValPort, ExtFnPort, Extrinsics

_P = TypeVar("_P", bound=Port)
_Q = TypeVar("_Q", bound=Port)
_BP = TypeVar("_BP", bound=BinaryNodePort)


@dataclasses.dataclass
class IVM(ExecutionContext):
    active_fast: list[tuple[Port, Port]] = field(default_factory=list)
    active_slow: list[tuple[Port, Port]] = field(default_factory=list)
    registers: list[Port | None] = field(default_factory=list)
    extrinsics: Extrinsics = field(default_factory=lambda: Extrinsics())

    def boot(self, g: Global, ext_val: ExtValPort):
        self.link(GlobalPort(global_ref=g), ext_val.fork())

    def link_register(self, register: int, port: Port) -> None:
        register_port = self.registers[register]
        if register_port is not None:
            self.registers[register] = None
            self.link(port, register_port)
        else:
            self.registers[register] = port

    def do_fast(self) -> Generator[None, None, None]:
        while self.active_fast:
            a, b = self.active_fast.pop()
            self.interact(a, b)
            yield

    def normalize(self) -> Generator[None, None, None]:
        while True:
            yield from self.do_fast()
            if self.active_slow:
                a, b = self.active_slow.pop()
                self.interact(a, b)
                yield
            else:
                break

    def link_wire_wire(self, a: Wire, b: Wire):
        return self.link_wire(a, WirePort(wire=b))

    def follow(self, a: Port, destructive: bool) -> Port:
        for wire, b in self.follow_each_wire(a):
            if b:
                a = b
        return a

    def follow_each_wire(self, a: Port) -> Iterator[tuple[Wire, Port | None]]:
        while isinstance(a, WirePort):
            wire = a.wire
            b = wire.load_target()
            yield wire, b
            if b:
                a = b
            else:
                break

    def link_wire(self, a: Wire, b: Port):
        b = self.follow(b, True)
        c = a.swap_target(b)
        if c:
            self.link(c, b)

    def link(self, a: Port, b: Port) -> None:
        if ports := _find_either_is(a, b, WirePort):
            a, b = ports
            self.link_wire(a.wire, b)
            return
        if _find_both_one_of(a, b, (GlobalPort, ErasePort)) or _find_both_one_of(
            a, b, (ExtValPort, ErasePort)
        ):
            if isinstance(a, ExtValPort):
                a.drop()
            if isinstance(b, ExtValPort):
                b.drop()
            return
        if (comb_ports := _find_both_are(a, b, BinaryNodePort)) and (
            type(a) is type(b) and isinstance(a, (CombPort, ExtFnPort))
        ):
            if comb_ports[0].label == comb_ports[1].label:
                self.active_fast.append(comb_ports)
                return
        if _find_either_is(a, b, GlobalPort) or _find_both_one_of(
            a, b, (CombPort, ExtFnPort, BranchPort)
        ):
            self.active_slow.append((a, b))
            return
        if (
            _find_either_is(a, b, ErasePort) is not None
            or _find_either_is(a, b, ExtValPort) is not None
        ):
            self.active_fast.append((a, b))
            return
        assert False, "unreachable"

    def interact(self, a: Port, b: Port) -> None:
        if _find_either_is(a, b, WirePort) or _find_both_one_of(
            a, b, (ErasePort, ExtValPort)
        ):
            assert False, "unreachable"
        if ports1 := _find_and_orient_both(a, b, GlobalPort, CombPort):
            if not ports1[0].global_ref.contains_label(ports1[1].label):
                self.copy(ports1[0], ports1[1])
                return
        if ports2 := _find_either_is(a, b, GlobalPort):
            self.expand(ports2[0], ports2[1])
            return
        if ports3 := _find_both_are(a, b, BinaryNodePort):
            if ports3[0].label == ports3[1].label:
                self.annihilate(ports3[0], ports3[1])
                return
            self.commute(ports3[0], ports3[1])
            return
        if ports4 := _find_and_orient_both(a, b, BranchPort, ExtValPort):
            self.branch(ports4[0], ports4[1])
            return
        if ports5 := _find_and_orient_both(a, b, ExtFnPort, ExtValPort):
            self.call(ports5[0], ports5[1])
            return
        if ports6 := _find_and_orient_both(a, b, NilaryNodePort, BinaryNodePort):
            self.copy(ports6[0], ports6[1])
            return
        assert False, "unreachable"

    def expand(self, a: GlobalPort, b: Port):
        self.execute(a.global_ref.instructions, b)

    def annihilate(self, a: BinaryNodePort, b: BinaryNodePort):
        a1, a2 = a.aux()
        b1, b2 = b.aux()
        self.link_wire_wire(a1, b1)
        self.link_wire_wire(a2, b2)

    def copy(self, a: NilaryNodePort, b: BinaryNodePort):
        x, y = b.aux()
        self.link_wire(x, a.fork())
        self.link_wire(y, a)

    def _copy_with_new_aux(self, b: _BP) -> tuple[_BP, Wire, Wire]:
        wire, wire_other = make_wire_pair()
        updated = dataclasses.replace(b, target=wire)
        return updated, wire, wire_other

    def commute(self, a: BinaryNodePort, b: BinaryNodePort):
        a1 = self._copy_with_new_aux(a)
        a2 = self._copy_with_new_aux(a)
        b1 = self._copy_with_new_aux(b)
        b2 = self._copy_with_new_aux(b)

        a_0_1, a_0_2 = a.aux()
        b_0_1, b_0_2 = b.aux()

        self.link_wire_wire(a1[1], b1[1])
        self.link_wire_wire(a1[2], b2[1])
        self.link_wire_wire(a2[1], b1[2])
        self.link_wire_wire(a2[2], b2[2])

        self.link_wire(a_0_1, b1[0])
        self.link_wire(a_0_2, b2[0])
        self.link_wire(b_0_1, a1[0])
        self.link_wire(b_0_2, a2[0])

    @staticmethod
    def _wrap_result(result):
        """Auto-wrap a plain value in ExtVal if it isn't already."""
        if isinstance(result, Port):
            return result
        return ExtVal(result)

    def call(self, a: ExtFnPort, b: ExtValPort):
        label = a.unwrap_label()

        # Split ext fn: one input -> two outputs
        if label in self.extrinsics.split_ext_fns:
            rhs, out = a.aux()
            result1, result2 = self.extrinsics.split_ext_fns[label](b.value)
            self.link_wire(rhs, self._wrap_result(result1))
            self.link_wire(out, self._wrap_result(result2))
            return

        # Merge ext fn: two inputs -> one output
        rhs, out = a.aux()
        rhs_port = rhs.load_target()
        if rhs_port:
            if isinstance(rhs_port, ExtValPort):
                rhs.target = None  # disconnect
                if a.swapped:
                    result = self.extrinsics.ext_fns[label](
                        rhs_port.value, b.value
                    )
                else:
                    result = self.extrinsics.ext_fns[label](
                        b.value, rhs_port.value
                    )
                self.link_wire(out, self._wrap_result(result))
                return

        new_fn = self._copy_with_new_aux(a.swap())
        self.link_wire(rhs, new_fn[0])
        self.link_wire(new_fn[1], b)
        self.link_wire_wire(new_fn[2], out)

    def branch(self, a: BranchPort, b: ExtValPort):
        b1, b2 = a.aux()
        branch, z, p = self._copy_with_new_aux(a)
        self.link_wire(b1, branch)
        if not b.value:
            y, n = z, p
        else:
            y, n = p, z
        self.link_wire(n, Port.ERASE)
        self.link_wire_wire(b2, y)

    def execute(self, instructions: Instructions, port: Port) -> None:
        needed_registers = max(instructions.next_register, 1)
        if needed_registers > len(self.registers):
            self.registers += [None] * (needed_registers - len(self.registers))

        self.link_register(0, port)

        for instruction in instructions:
            new_inert = instruction.execute(self)
            if new_inert:
                pass  # inert pairs are unused without debugger

        for register in self.registers:
            assert (
                register is None
            ), f"Found unempty register {register}, instructions did not complete cleanly"


def _find_either_is(a: Port, b: Port, goal: type[_P]) -> tuple[_P, Port] | None:
    if isinstance(a, goal):
        return a, b
    if isinstance(b, goal):
        return b, a
    return None


def _find_both_are(a: Port, b: Port, goal: type[_P]) -> tuple[_P, _P] | None:
    if isinstance(a, goal) and isinstance(b, goal):
        return a, b
    return None


def _find_both_one_of(
    a: Port, b: Port, at: Iterable[type[Port]]
) -> tuple[Port, Port] | None:
    for t in at:
        if isinstance(a, t):
            break
    else:
        return None
    for t in at:
        if isinstance(b, t):
            return a, b
    return None


def _find_and_orient_both(
    a: Port, b: Port, goal_a: type[_P], goal_b: type[_Q]
) -> tuple[_P, _Q] | None:
    if isinstance(a, goal_a) and isinstance(b, goal_b):
        return a, b
    if isinstance(b, goal_a) and isinstance(a, goal_b):
        return b, a
    return None
