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


def normalize_dfa(dfa: dict) -> dict:
    """Convierte un DFA (posiblemente cargado desde JSON con claves string)
    a un dict con claves enteras. Centralizado aquí para evitar duplicación
    entre lexer_builder.py y codegen.py."""
    trans: Dict[int, Dict[str, int]] = {}
    for state, row in dfa.get('trans', {}).items():
        trans[int(state)] = {symbol: int(dest) for symbol, dest in row.items()}

    accept: Dict[int, dict] = {}
    for state, info in dfa.get('accept', {}).items():
        if isinstance(info, dict):
            accept[int(state)] = {
                'priority': int(info.get('priority', 0)),
                'token':    info.get('token'),
                'ignore':   bool(info.get('ignore', False)),
            }
        else:
            priority, token, ignore = info
            accept[int(state)] = {
                'priority': int(priority),
                'token':    token,
                'ignore':   bool(ignore),
            }

    return {
        'start':        int(dfa.get('start', 0)),
        'trans':        trans,
        'accept':       accept,
        'ignore_tokens': set(dfa.get('ignore_tokens', [])),
    }