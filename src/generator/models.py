"""Modelos de datos para lexer y parser."""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class LexRule:
    token: str
    regex: str
    ignore: bool = False


@dataclass
class YalSpec:
    rules: List[LexRule]


@dataclass
class Grammar:
    terminals: Set[str]
    non_terminals: Set[str]
    start_symbol: str
    productions: Dict[str, List[List[str]]]
    ignore_tokens: Set[str] = field(default_factory=set)


@dataclass(frozen=True)
class Item:
    lhs: str
    rhs: Tuple[str, ...]
    dot: int

    def next_symbol(self):
        return self.rhs[self.dot] if self.dot < len(self.rhs) else None

    def advance(self):
        return Item(self.lhs, self.rhs, self.dot + 1)
