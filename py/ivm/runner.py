import importlib
import sys
import os.path
import argparse

from ivm.compat import add_std_compat
from ivm.extrinsics import PrimitiveExtValPort
from ivm.host import Host


def main():
    parser = argparse.ArgumentParser(description="A python ivm runner")
    parser.add_argument("--file", type=str, help="iv file to be run")
    parser.add_argument(
        "--extension",
        dest="extensions",
        help="python.module.path:function_name to run on the Host object before execution",
    )
    args = parser.parse_args()

    host = Host()
    add_std_compat(host)

    if args.extensions:
        for extension in args.extensions:
            module_name, function_name = extension.split(":")
            module = importlib.import_module(module_name)
            getattr(module, function_name)(host)

    if os.path.isfile(args.file):
        host.parse_file(args.file)
    else:
        print(f"File not found: {args.file}", file=sys.stderr)

    host.boot("::main", PrimitiveExtValPort(0))
    host.execute()

if __name__ == "__main__":
    main()
