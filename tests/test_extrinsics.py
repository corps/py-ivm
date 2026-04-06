from ivm.extrinsics import PrimitiveExtValPort, Extrinsics


def test_primitive_ext_val_fork():
    val = PrimitiveExtValPort(42)
    forked = val.fork()
    assert forked is val


def test_primitive_ext_val_drop():
    val = PrimitiveExtValPort(42)
    val.drop()  # should be no-op


def test_extrinsics_registration():
    ext = Extrinsics()
    fn = lambda a, b: PrimitiveExtValPort(a + b)
    ext.ext_fns["n32_add"] = fn
    result = ext.ext_fns["n32_add"](3, 5)
    assert isinstance(result, PrimitiveExtValPort)
    assert result.value == 8


def test_n32_values():
    a = PrimitiveExtValPort(100)
    b = PrimitiveExtValPort(100)
    assert a.value == b.value
    c = PrimitiveExtValPort(200)
    assert a.value != c.value


def test_f32_values():
    a = PrimitiveExtValPort(3.14)
    b = PrimitiveExtValPort(3.14)
    assert a.value == b.value
    c = PrimitiveExtValPort(2.71)
    assert a.value != c.value
