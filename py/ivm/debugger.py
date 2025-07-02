import dataclasses
import io
from collections import OrderedDict
from typing import Iterator

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, Horizontal
from textual.content import Content
from textual.events import Resize
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Footer, Header, Static, RichLog

from ivm.globals import Instruction, Nilary, Binary
from ivm.heap import Port, Wire, WirePort, BinaryNodePort, SourceInfo
from ivm.host import Host
from ivm.readback import Reader
from ivm.tree import (
    Tree,
    Erase,
    N32Node,
    F32Node,
    CombNode,
    ExtFnNode,
    BranchNode,
    VarNode,
    GlobalNode,
    Net,
)


@dataclasses.dataclass
class History:
    interaction_stack: tuple[tuple[Tree, Tree, str], ...] = ()
    stack: tuple[tuple[Tree, Tree], ...] = ()
    stdout: str = ""
    stderr: str = ""
    stdin: str = ""


class Inline(Static):
    DEFAULT_CSS = """
    """


class Word(Inline):
    DEFAULT_CSS = """
    Word {
        width: 12
    }
    """


tree_colors: dict[type, str] = {
    Erase: "white",
    N32Node: "rgb(135,215,255)",
    F32Node: "rgb(135,215,255)",
    CombNode: "rgb(215,135,0)",
    ExtFnNode: "rgb(95,95,255)",
    BranchNode: "white",
    VarNode: "rgb(95,0,175)",
    GlobalNode: "magenta",
}


class TreeView(Static):
    view_tree: reactive[Tree] = reactive(Erase(None))

    DEFAULT_CSS = """
    TreeView {
        width: 1fr;
        margin-bottom: 1;
    }
    """

    def __init__(self, tree: Tree):
        super().__init__()
        self.view_tree = tree

    def _render_tree(self, n: Tree, width: int, indention: int) -> Iterator[Text]:
        s = str(n)
        if n.has_children and width > 0:
            if len(s) + indention > width:
                yield Text.assemble(
                    " " * indention, (n.head(), tree_colors[type(n)]), "("
                )
                for c in n:
                    yield from self._render_tree(c, width, indention + 2)
                yield Text.assemble(" " * indention, ")")
                return
        yield (
            Text.assemble(
                " " * indention,
                (n.head(), tree_colors[type(n)]),
                *("(" for _ in range(n.has_children)),
                *(
                    part
                    for i, c in enumerate(n)
                    for part in (
                        *(Text(" ") for _ in range(i > 0)),
                        *self._render_tree(c, width, 0),
                    )
                ),
                *(")" for _ in range(n.has_children)),
                end="",
            )
        )

    def on_resize(self, event: Resize) -> None:
        self._render_to_width(event.size.width)

    def _render_to_width(self, width: int) -> None:
        self.update(
            Text("\n").join(
                (part for part in self._render_tree(self.view_tree, width, 0))
            )
        )

    def watch_view_tree(self, tree: Tree):
        if isinstance(tree.trace, SourceInfo):
            source = tree.trace.containing_net_source
            line, (s, e) = tree.trace.head_span
            self.tooltip = Content.assemble(
                *(l + "\n" for l in source[:line]),
                source[line][:s],
                (source[line][s:e], "bold red"),
                source[line][e:],
                "\n",
                *(l + "\n" for l in source[line + 1 :]),
            )
        else:
            self.tooltip = None

        self._render_to_width(self.size.width)


class HistoryChart(Widget):
    DEFAULT_CSS = """
    HistoryChart {
        border: solid white;
    }
    
    .stack {
        height: auto;
        width: 100%;
        overflow-y: scroll;
        overflow-x: hidden;
    }
    
    .stdout, .stderr, .stdin {
        height: 3;
    }
    
    .stdin Word, .stderr Word, .stdout Word {
        margin: 1 0;
    }
    """

    history: reactive[History | None] = reactive(None, recompose=True)

    def compose(self) -> ComposeResult:
        cur: History = self.history
        if cur is None:
            yield Static("")
            return

        for a, b in cur.stack:
            with Horizontal(classes="stack"):
                yield Word("> ")
                yield TreeView(a)
                yield TreeView(b)

        yield HorizontalGroup()

        for a, b, interaction in cur.interaction_stack:
            with Horizontal(classes="stack"):
                yield Word(interaction)
                yield TreeView(a)
                yield TreeView(b)

class DebuggerApp(App):
    host: Host
    reader: Reader
    history: list[History]
    cur_idx: reactive[int] = reactive(-1)

    DEFAULT_CSS = """
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("{", "prev", "Back"),
        ("}", "next", "Next"),
        ("w", "focus_next", "Focus Next"),
        ("b", "focus_previous", "Focus Back"),
    ]

    def __init__(self, host: Host):
        self.host = host
        self.reader = Reader(host.ivm)
        self.history = track_history(host)
        super().__init__()

    def action_next(self):
        if len(self.history) > self.cur_idx + 1:
            self.cur_idx += 1
        else:
            self.title = f"⏳ Running..."
            next(self.host.ivm.normalize(), None)
            if len(self.history) > self.cur_idx + 1:
                self.cur_idx += 1
        self.update_from_history()

    def action_prev(self):
        if self.cur_idx > 0:
            self.cur_idx -= 1
        self.update_from_history()

    def update_from_history(self):
        if self.cur_idx >= 0:
            self.title = f"Step {self.cur_idx}"
        else:
            self.title = "Run 'next' to start"

        if self.cur_idx >= len(self.history) or self.cur_idx < 0:
            return

        history = self.history[self.cur_idx]
        self.query_one(HistoryChart).history = history

    def compose(self) -> ComposeResult:
        yield Header()
        yield HistoryChart()
        yield Footer()

    def on_mount(self):
        self.update_from_history()


def attach_debugger_to(
    host: Host,
) -> DebuggerApp:
    return DebuggerApp(host)


def track_history(host: Host) -> list[History]:
    history: list[History] = []
    reader = Reader(host.ivm)
    interaction_stack: list[tuple[Tree, Tree, str]] = []

    def add_history():
        history.append(
            History(
                interaction_stack=tuple(interaction_stack),
                stack=tuple(
                    (
                        reader.read_port(a, shallow=False),
                        reader.read_port(b, shallow=False),
                    )
                    for stack in (host.ivm.active_slow, host.ivm.active_fast)
                    for a, b in stack
                ),
                stdout=(
                    host.stdout.buffer.getvalue().decode("utf-8")
                    if isinstance(host.stdout.buffer, io.BytesIO)
                    else ""
                ),
                stderr=(
                    host.stderr.buffer.getvalue().decode("utf-8")
                    if isinstance(host.stderr.buffer, io.BytesIO)
                    else ""
                ),
                stdin=(
                    host.stdin.buffer.getvalue().decode("utf-8")
                    if isinstance(host.stdin.buffer, io.BytesIO)
                    else ""
                ),
            )
        )

    def on_start_interaction(a: Port, b: Port, interaction: str):
        interaction_stack.append(
            (
                reader.read_port(a, shallow=False),
                reader.read_port(b, shallow=False),
                interaction,
            )
        )
        add_history()

    def on_complete_interaction():
        interaction_stack.pop()
        add_history()

    host.ivm.on_complete_interaction = on_complete_interaction
    host.ivm.on_start_interaction = on_start_interaction
    return history
