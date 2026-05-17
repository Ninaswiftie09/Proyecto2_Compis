"""Motor de expresiones regulares propio basado en Thompson.

No utiliza librerías de expresiones regulares. Soporta un subconjunto útil para
YALex: concatenación implícita, unión |, *, +, ?, paréntesis, escapes comunes,
clases de caracteres [a-zA-Z0-9_], y espacios escapados.
"""
from collections import defaultdict, deque

EPS = 'ε'
CONCAT = '·'

_OPERATORS = {'|', CONCAT, '*', '+', '?', '(', ')'}
_POSTFIX_OPS = {'|', CONCAT, '*', '+', '?'}


def _literal(ch: str):
    return ('lit', ch)


def _is_literal(tok) -> bool:
    return isinstance(tok, tuple) and len(tok) == 2 and tok[0] == 'lit'


def _escape_value(ch: str) -> str:
    values = {'n': '\n', 't': '\t', 'r': '\r', 's': ' '}
    return values.get(ch, ch)


def _expand_class(pattern: str, start: int):
    """Lee una clase [..] y devuelve tokens equivalentes a (a|b|c)."""
    chars = []
    i = start + 1
    if i < len(pattern) and pattern[i] == '^':
        raise ValueError('Las clases negadas [^...] no están soportadas por este generador.')
    while i < len(pattern):
        if pattern[i] == ']':
            if not chars:
                raise ValueError('Clase de caracteres vacía [] en expresión regular.')
            toks = ['(']
            for pos, ch in enumerate(chars):
                if pos:
                    toks.append('|')
                toks.append(_literal(ch))
            toks.append(')')
            return toks, i + 1
        if pattern[i] == '\\':
            if i + 1 >= len(pattern):
                raise ValueError('Escape incompleto dentro de clase de caracteres.')
            chars.append(_escape_value(pattern[i + 1]))
            i += 2
            continue
        if i + 2 < len(pattern) and pattern[i + 1] == '-' and pattern[i + 2] != ']':
            a, b = pattern[i], pattern[i + 2]
            if ord(a) > ord(b):
                raise ValueError(f'Rango inválido [{a}-{b}] en expresión regular.')
            for code in range(ord(a), ord(b) + 1):
                chars.append(chr(code))
            i += 3
            continue
        chars.append(pattern[i])
        i += 1
    raise ValueError('Clase de caracteres sin cerrar en expresión regular.')


def tokenize_regex(pattern: str):
    tokens = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c.isspace():
            i += 1
            continue
        if c == '\\':
            if i + 1 >= len(pattern):
                raise ValueError('Escape incompleto al final de expresión regular.')
            tokens.append(_literal(_escape_value(pattern[i + 1])))
            i += 2
        elif c == '[':
            class_tokens, i = _expand_class(pattern, i)
            tokens.extend(class_tokens)
        elif c in {'(', ')', '*', '+', '?', '|'}:
            tokens.append(c)
            i += 1
        else:
            tokens.append(_literal(c))
            i += 1
    if not tokens:
        raise ValueError('Expresión regular vacía.')
    return tokens


def _can_end_atom(tok) -> bool:
    return _is_literal(tok) or tok == ')' or tok in {'*', '+', '?'}


def _can_start_atom(tok) -> bool:
    return _is_literal(tok) or tok == '('


def add_concat(tokens):
    out = []
    for i, tok in enumerate(tokens):
        out.append(tok)
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if _can_end_atom(tok) and _can_start_atom(nxt):
                out.append(CONCAT)
    return out


def to_postfix(tokens):
    precedence = {'|': 1, CONCAT: 2, '?': 3, '*': 3, '+': 3}
    out, stack = [], []
    for tok in tokens:
        if _is_literal(tok):
            out.append(tok)
        elif tok == '(':
            stack.append(tok)
        elif tok == ')':
            while stack and stack[-1] != '(':
                out.append(stack.pop())
            if not stack:
                raise ValueError('Paréntesis de cierre sin apertura en expresión regular.')
            stack.pop()
        elif tok in precedence:
            while stack and stack[-1] != '(' and precedence.get(stack[-1], 0) >= precedence[tok]:
                out.append(stack.pop())
            stack.append(tok)
        else:
            raise ValueError(f'Token regex no reconocido: {tok!r}')
    while stack:
        if stack[-1] == '(':
            raise ValueError('Paréntesis de apertura sin cierre en expresión regular.')
        out.append(stack.pop())
    return out


def thompson(postfix):
    next_state = 0
    trans = defaultdict(lambda: defaultdict(set))

    def ns():
        nonlocal next_state
        state = next_state
        next_state += 1
        return state

    stack = []
    for tok in postfix:
        if _is_literal(tok):
            a, b = ns(), ns()
            trans[a][tok[1]].add(b)
            stack.append((a, b))
        elif tok == CONCAT:
            if len(stack) < 2:
                raise ValueError('Concatenación inválida en expresión regular.')
            a2, b2 = stack.pop()
            a1, b1 = stack.pop()
            trans[b1][EPS].add(a2)
            stack.append((a1, b2))
        elif tok == '|':
            if len(stack) < 2:
                raise ValueError('Unión inválida en expresión regular.')
            a2, b2 = stack.pop()
            a1, b1 = stack.pop()
            s, e = ns(), ns()
            trans[s][EPS].update({a1, a2})
            trans[b1][EPS].add(e)
            trans[b2][EPS].add(e)
            stack.append((s, e))
        elif tok == '*':
            if not stack:
                raise ValueError('Operador * sin operando.')
            a, b = stack.pop()
            s, e = ns(), ns()
            trans[s][EPS].update({a, e})
            trans[b][EPS].update({a, e})
            stack.append((s, e))
        elif tok == '+':
            if not stack:
                raise ValueError('Operador + sin operando.')
            a, b = stack.pop()
            s, e = ns(), ns()
            trans[s][EPS].add(a)
            trans[b][EPS].update({a, e})
            stack.append((s, e))
        elif tok == '?':
            if not stack:
                raise ValueError('Operador ? sin operando.')
            a, b = stack.pop()
            s, e = ns(), ns()
            trans[s][EPS].update({a, e})
            trans[b][EPS].add(e)
            stack.append((s, e))
        else:
            raise ValueError(f'Operador regex no reconocido: {tok!r}')
    if len(stack) != 1:
        raise ValueError('Expresión regular inválida o incompleta.')
    return stack[-1], trans


def all_states(trans, start=None, end=None):
    states = set()
    if start is not None:
        states.add(start)
    if end is not None:
        states.add(end)
    for src, row in trans.items():
        states.add(src)
        for dests in row.values():
            states.update(dests)
    return states


def epsilon_closure(states, trans):
    q, seen = deque(states), set(states)
    while q:
        state = q.popleft()
        for nxt in trans[state].get(EPS, set()):
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return frozenset(seen)
