"""Modelos de datos usados por el generador léxico y sintáctico."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

EPSILON = 'ε'
ENDMARK = '$'


@dataclass
class LexRule:
    token: str
    regex: str
    ignore: bool = False
    source_line: int = 0


@dataclass
class YalSpec:
    rules: List[LexRule]
    definitions: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class Grammar:
    terminals: Set[str]
    non_terminals: Set[str]
    start_symbol: str
    productions: Dict[str, List[List[str]]]
    ignore_tokens: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True, order=True)
class Item:
    lhs: str
    rhs: Tuple[str, ...]
    dot: int

    def next_symbol(self) -> Optional[str]:
        return self.rhs[self.dot] if self.dot < len(self.rhs) else None

    def advance(self) -> 'Item':
        return Item(self.lhs, self.rhs, self.dot + 1)
