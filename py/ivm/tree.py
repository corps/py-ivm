import abc
import dataclasses
from dataclasses import dataclass
from math import isnan
from typing import (
    OrderedDict,
    Iterator,
)


class Tree(abc.ABC):
    @abc.abstractmethod
    def __iter__(self) -> "Iterator[Tree]": ...

    has_children: bool = False

    @abc.abstractmethod
    def head(self) -> str: ...


@dataclasses.dataclass
class Erase(Tree):
    def __str__(self):
        return "_"

    __repr__ = __str__

    has_children: bool = False

    def __iter__(self) -> Iterator[Tree]:
        return iter(())

    def head(self) -> str:
        return str(self)


@dataclasses.dataclass
class CombNode(Tree):
    label: str
    left: "Tree"
    right: "Tree"

    def __str__(self):
        if not hasattr(self, "_str"):
            self._str = f"{self.label}({self.left} {self.right})"
        return self._str

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        yield self.left
        yield self.right

    has_children: bool = True

    def head(self) -> str:
        return self.label


@dataclasses.dataclass
class ExtFnNode(Tree):
    label: str
    left: "Tree"
    right: "Tree"

    def __str__(self):
        if not hasattr(self, "_str"):
            self._str = f"@{self.label}({self.left} {self.right})"
        return self._str

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        yield self.left
        yield self.right

    has_children: bool = True

    def head(self) -> str:
        return "@" + self.label


@dataclasses.dataclass
class BranchNode(Tree):
    n0: "Tree"
    n1: "Tree"
    n2: "Tree"

    def __str__(self):
        if not hasattr(self, "_str"):
            self._str = f"?({self.n0} {self.n1} {self.n2})"
        return self._str

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        yield self.n0
        yield self.n1
        yield self.n2

    has_children: bool = True

    def head(self) -> str:
        return "?"


@dataclasses.dataclass
class N32Node(Tree):
    value: int

    def __str__(self):
        return str(self.value)

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(())

    def head(self) -> str:
        return str(self.value)


@dataclasses.dataclass
class F32Node(Tree):
    value: float

    def __str__(self):
        if isnan(self.value):
            return "+NaN"
        return str(self.value)

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(())

    def head(self) -> str:
        return str(self.value)


@dataclasses.dataclass
class VarNode(Tree):
    name: str

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(())

    def head(self) -> str:
        return self.name


@dataclasses.dataclass
class GlobalNode(Tree):
    name: str

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(())

    def head(self) -> str:
        return self.name


@dataclasses.dataclass
class BlackBox(Tree):
    inner: "Tree"

    def __str__(self):
        return f"{self.inner}"

    __repr__ = __str__

    def __iter__(self) -> Iterator[Tree]:
        return iter(self.inner)

    def head(self) -> str:
        return self.inner.head()


@dataclass(frozen=True)
class Net:
    root: Tree
    pairs: tuple[tuple[Tree, Tree], ...] = ()

    def __str__(self):
        if not self.pairs:
            return " ".join(["{{", str(self.root), "}}"])
        return "\n  ".join(
            [
                "{{",
                str(self.root),
                *[f"{a} = {b}" for a, b in self.pairs],
                "}}",
            ]
        )

    def __iter__(self) -> Iterator[Tree]:
        q = [self.root, *(p for pairs in self.pairs for p in pairs)]
        while q:
            t = q.pop()
            yield t
            q.extend(t)


Nets = OrderedDict[str, Net]
