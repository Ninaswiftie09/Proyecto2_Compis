"""Modelos de datos usados por el generador léxico y sintáctico."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

EPSILON = 'ε'# cadena vacía y el inicio de la entrada
ENDMARK = '$' # fin de la entrada


# Es una regla lexica que se saca del yal
@dataclass
class LexRule:
    token: str
    regex: str
    ignore: bool = False
    source_line: int = 0

# guarda las especificaciones lexicas 
@dataclass
class YalSpec:
    rules: List[LexRule]
    definitions: Dict[str, str] = field(default_factory=dict) # definiciones let
    warnings: List[str] = field(default_factory=list)

# guarda la gramatica que esta en el yalp
@dataclass
class Grammar:
    terminals: Set[str]
    non_terminals: Set[str]
    start_symbol: str
    productions: Dict[str, List[List[str]]]
    ignore_tokens: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)


# representa un item LR(0)
@dataclass(frozen=True, order=True)
class Item:
    lhs: str
    rhs: Tuple[str, ...]
    dot: int # indica en que posicion va el parser

    # devuelve el simbolo después del punto
    def next_symbol(self) -> Optional[str]:
        return self.rhs[self.dot] if self.dot < len(self.rhs) else None

    # mueve el punto de posición hacia adeltante
    def advance(self) -> 'Item':
        return Item(self.lhs, self.rhs, self.dot + 1)

# normaliza el AFD para que las claves de estados sean enteros.
def normalize_dfa(dfa: dict) -> dict:
    """Convierte un DFA a un dict con claves enteras. Centralizado aquí para evitar duplicación
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