import struct
from typing import Any, Callable

from ivm.extrinsics import ExtVal
from ivm.host import Host

_U32_MASK = 0xFFFFFFFF


def _f32(x: float) -> float:
    """Truncate a Python float to f32 precision."""
    return struct.unpack('f', struct.pack('f', x))[0]


def add_std_compat(host: Host) -> None:
    def merge_ext_fn(c: Callable):
        host.add_ext_fun(c)

    @merge_ext_fn
    def io_print_byte(io, b):
        host.stdout.buffer.write((b & 0xFF).to_bytes(1))
        return 0

    @merge_ext_fn
    def io_flush(io, _):
        host.stdout.flush()
        return 0

    @merge_ext_fn
    def n32_sub(a, b):
        return (a - b) & _U32_MASK

    @merge_ext_fn
    def n32_add(a, b):
        return (a + b) & _U32_MASK

    @merge_ext_fn
    def n32_eq(a, b):
        return int(a == b)

    @merge_ext_fn
    def n32_ne(a, b):
        return int(a != b)

    @merge_ext_fn
    def n32_mul(a, b):
        return (a * b) & _U32_MASK

    @merge_ext_fn
    def n32_rem(a, b):
        return (a % b) & _U32_MASK

    @merge_ext_fn
    def n32_div(a, b):
        return (a // b) & _U32_MASK

    @merge_ext_fn
    def n32_lt(a, b):
        return int(a < b)

    @merge_ext_fn
    def f32_sub(a, b):
        return _f32(a - b)

    @merge_ext_fn
    def f32_add(a, b):
        return _f32(a + b)

    @merge_ext_fn
    def f32_eq(a, b):
        return _f32(float(a == b))

    @merge_ext_fn
    def f32_ne(a, b):
        return _f32(float(a != b))

    @merge_ext_fn
    def f32_mul(a, b):
        return _f32(a * b)

    @merge_ext_fn
    def f32_rem(a, b):
        return _f32(a % b)

    @merge_ext_fn
    def f32_div(a, b):
        return _f32(a / b)

    @merge_ext_fn
    def f32_lt(a, b):
        return _f32(float(a < b))

    # io_read_byte is a split ext fn: takes IO token, returns (byte, io_continuation)
    def io_read_byte(io):
        result = host.stdin.buffer.read(1)[:1]
        if not result:
            return 0xFFFFFFFF, 0
        return int.from_bytes(result), 0

    host.ivm.extrinsics.split_ext_fns["io_read_byte"] = io_read_byte

    # Aliases for upstream compatibility
    host.ivm.extrinsics.ext_fns["io_print_char"] = io_print_byte
    host.ivm.extrinsics.split_ext_fns["io_read_char"] = io_read_byte
