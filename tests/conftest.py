import os
import sys
from io import BytesIO, TextIOWrapper

import pytest

from ivm.compat import add_std_compat
from ivm.extrinsics import PrimitiveExtValPort
from ivm.host import Host

PROGRAMS_DIR = os.path.join(os.path.dirname(__file__), "programs")


@pytest.fixture
def host():
    stdout = TextIOWrapper(BytesIO())
    stdin = TextIOWrapper(BytesIO())
    h = Host(stdout=stdout, stdin=stdin)
    add_std_compat(h)
    return h


def run_program(host, filename, stdin_data=None):
    if stdin_data is not None:
        host.stdin = TextIOWrapper(BytesIO(stdin_data.encode()))
    filepath = os.path.join(PROGRAMS_DIR, filename)
    host.parse_file(filepath)
    host.boot("::main", PrimitiveExtValPort(0))
    host.execute()
    host.stdout.flush()
    return host.stdout.buffer.getvalue().decode()
