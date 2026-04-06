import dataclasses

from ivm.extrinsics import PrimitiveExtValPort, ExtFnPort, Extrinsics
from ivm.globals import GlobalPort, Global, Instructions, Nilary, Binary
from ivm.heap import (
    ErasePort,
    CombPort,
    BranchPort,
    WirePort,
    make_wire_pair,
)
from ivm.vm import IVM


def make_ivm(**kwargs):
    return IVM(**kwargs)


def run_to_normal(ivm):
    for _ in ivm.normalize():
        pass


def test_annihilate():
    """Same-label binary nodes cancel out, linking their aux ports."""
    ivm = make_ivm()
    w1 = make_wire_pair()[0]
    w2 = make_wire_pair()[0]
    a = CombPort(label="x", target=w1)
    b = CombPort(label="x", target=w2)
    val1 = PrimitiveExtValPort((42))
    val2 = PrimitiveExtValPort((99))
    w1.target = val1
    w1.other_half.target = val2
    ivm.link(a, b)
    run_to_normal(ivm)
    # After annihilation, w2's aux ports should have the values from w1
    assert isinstance(w2.load_target(), PrimitiveExtValPort)
    assert w2.load_target().value == (42)


def test_copy_erase():
    """Erase node copies to both aux ports of a binary node."""
    ivm = make_ivm()
    w = make_wire_pair()[0]
    comb = CombPort(label="x", target=w)
    erase = ErasePort()
    ivm.link(erase, comb)
    run_to_normal(ivm)
    # Both aux wires should have erase ports
    assert isinstance(w.load_target(), ErasePort)
    assert isinstance(w.other_half.load_target(), ErasePort)


def test_copy_extval():
    """ExtVal copies to both aux ports of a binary node."""
    ivm = make_ivm()
    w = make_wire_pair()[0]
    comb = CombPort(label="x", target=w)
    val = PrimitiveExtValPort((7))
    ivm.link(val, comb)
    run_to_normal(ivm)
    assert isinstance(w.load_target(), PrimitiveExtValPort)
    assert isinstance(w.other_half.load_target(), PrimitiveExtValPort)


def test_branch_zero():
    """Branch with value 0 takes the zero/false path."""
    ivm = make_ivm()
    # ?(n0 n1 n2) → creates two branches:
    # inner: Branch("", aux1=n0, aux2=n1)
    # outer: Branch("", aux1=inner, aux2=n2)
    # When value is 0: inner branch is connected, n2 is erased
    # When value is nonzero: n2 is connected, inner is erased

    # Build the structure via instruction serialization (simpler)
    g = Global(name="::test_branch")
    instr = g.instructions
    # Register 0: input value
    # ?(val zero_result nonzero_result)
    r_val = instr.new_register()  # 1
    r_zero = instr.new_register()  # 2
    r_nonzero = instr.new_register()  # 3

    # The branch compiles to two Binary instructions
    r_inner = instr.new_register()  # 4
    instr.append(Nilary(r_val, PrimitiveExtValPort((100))))
    instr.append(Nilary(r_zero, PrimitiveExtValPort((200))))
    instr.append(Nilary(r_nonzero, PrimitiveExtValPort((300))))
    instr.append(Binary("Branch", "", r_inner, r_val, r_zero))
    instr.append(Binary("Branch", "", 0, r_inner, r_nonzero))

    # Boot with condition = 0
    ivm.link(GlobalPort(global_ref=g), PrimitiveExtValPort((0)))
    run_to_normal(ivm)


def test_branch_nonzero():
    """Branch with nonzero value takes the nonzero/true path."""
    ivm = make_ivm()
    g = Global(name="::test_branch")
    instr = g.instructions
    r_val = instr.new_register()
    r_zero = instr.new_register()
    r_nonzero = instr.new_register()
    r_inner = instr.new_register()
    instr.append(Nilary(r_val, PrimitiveExtValPort((100))))
    instr.append(Nilary(r_zero, PrimitiveExtValPort((200))))
    instr.append(Nilary(r_nonzero, PrimitiveExtValPort((300))))
    instr.append(Binary("Branch", "", r_inner, r_val, r_zero))
    instr.append(Binary("Branch", "", 0, r_inner, r_nonzero))

    ivm.link(GlobalPort(global_ref=g), PrimitiveExtValPort((1)))
    run_to_normal(ivm)


def test_call_ext_fn():
    """External function call with both args ready."""
    ivm = make_ivm()
    ivm.extrinsics.ext_fns["n32_add"] = lambda a, b: PrimitiveExtValPort(a + b)

    w = make_wire_pair()[0]
    rhs = PrimitiveExtValPort((3))
    w.target = rhs

    fn = ExtFnPort(label="n32_add", target=w)
    lhs = PrimitiveExtValPort((5))

    ivm.link(fn, lhs)
    run_to_normal(ivm)
    # Result should be on the out wire
    result = w.other_half.load_target()
    assert isinstance(result, PrimitiveExtValPort)
    assert result.value == (8)


def test_expand_global():
    """Expanding a global executes its instructions."""
    ivm = make_ivm()
    g = Global(name="::test")
    # Global that puts an erase in register 0
    g.instructions.append(Nilary(0, ErasePort()))

    # When global meets an ext val, expand puts the ext val in reg 0,
    # then the Nilary links erase with it (erase + ext val → both drop)
    ivm.link(GlobalPort(global_ref=g), PrimitiveExtValPort((42)))
    run_to_normal(ivm)


def test_expand_global_with_comb():
    """Expanding a global that produces a comb node."""
    ivm = make_ivm()
    g = Global(name="::test")
    # Global: { x(a b) a = _ b = _ }
    r_a = g.instructions.new_register()  # 1
    r_b = g.instructions.new_register()  # 2
    g.instructions.append(Nilary(r_a, ErasePort()))
    g.instructions.append(Nilary(r_b, ErasePort()))
    g.instructions.append(Binary("Comb", "x", 0, r_a, r_b))
    g.add_label("x")

    w = make_wire_pair()[0]
    comb = CombPort(label="x", target=w)

    ivm.link(GlobalPort(global_ref=g), comb)
    run_to_normal(ivm)
    # After expand: global produces CombPort("x") which annihilates with the other CombPort("x")
    # The annihilation links the aux wires, and erases flow through
    assert isinstance(w.load_target(), ErasePort)
    assert isinstance(w.other_half.load_target(), ErasePort)


def test_commute():
    """Different-label binary nodes commute (create intermediate nodes)."""
    ivm = make_ivm()
    w1 = make_wire_pair()[0]
    w2 = make_wire_pair()[0]

    a = CombPort(label="x", target=w1)
    b = CombPort(label="y", target=w2)

    # Put erases on all aux ports to let the interaction complete
    w1.target = ErasePort()
    w1.other_half.target = ErasePort()
    w2.target = ErasePort()
    w2.other_half.target = ErasePort()

    ivm.link(a, b)
    run_to_normal(ivm)
