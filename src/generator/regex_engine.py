"""Motor de expresiones regulares propio basado en Thompson.

"""
from collections import defaultdict, deque

EPS = 'ε'
CONCAT = '·'

_OPERATORS = {'|', CONCAT, '*', '+', '?', '(', ')'} # operadores posibles de regex
_POSTFIX_OPS = {'|', CONCAT, '*', '+', '?'} # operadores en posfix

# convierte un caracter normal a un literal interno 
def _literal(ch: str):
    return ('lit', ch)

# verifica si un token es un literal interno
def _is_literal(tok) -> bool:
    return isinstance(tok, tuple) and len(tok) == 2 and tok[0] == 'lit'

# convierte escapes en caractereas reales (tabs, espacio, saltos)
def _escape_value(ch: str) -> str:
    values = {'n': '\n', 't': '\t', 'r': '\r', 's': ' '}
    return values.get(ch, ch)

# lee literales entre comillas simples
def _read_quoted_literal(pattern: str, start: int):
    if start >= len(pattern) or pattern[start] != "'":
        raise ValueError('Se esperaba una comilla simple al leer literal YALex.')

    chars = []
    i = start + 1
    while i < len(pattern):
        ch = pattern[i]
        if ch == "'":
            if not chars:
                raise ValueError("Literal vacío '' en expresión regular.")
            return chars, i + 1
        if ch == '\\':
            if i + 1 >= len(pattern):
                raise ValueError('Escape incompleto dentro de literal entre comillas simples.')
            chars.append(_escape_value(pattern[i + 1]))
            i += 2
        else:
            chars.append(ch)
            i += 1

    raise ValueError('Literal entre comillas simples sin cerrar en expresión regular.')

# Detecta si una clase de caracteres usa comillas simples adentro
def _class_contains_quoted_items(pattern: str, start: int) -> bool:
    """Indica si una clase [...] contiene elementos entre comillas simples."""
    i = start + 1
    while i < len(pattern):
        if pattern[i] == '\\':
            i += 2
            continue
        if pattern[i] == ']':
            return False
        if pattern[i] == "'":
            return True
        i += 1
    return False

# lee un elemento dentro de una clase y devuelve una lista de caracteres y el indice siguiente
def _read_class_atom(pattern: str, i: int):
    """Lee un elemento dentro de una clase de caracteres.
    """
    if i >= len(pattern):
        raise ValueError('Clase de caracteres sin cerrar en expresión regular.')

    if pattern[i] == "'":
        return _read_quoted_literal(pattern, i)

    if pattern[i] == '\\':
        if i + 1 >= len(pattern):
            raise ValueError('Escape incompleto dentro de clase de caracteres.')
        return [_escape_value(pattern[i + 1])], i + 2

    return [pattern[i]], i + 1

# Convierte una clase de caracteres en una expresión equivalente con uniones
def _expand_class(pattern: str, start: int):
    """Lee una clase [..] y devuelve tokens equivalentes a (a|b|c).

    Soporta los dos estilos:
      [0-9]
      ['0'-'9']
      [' ' '\\t' '\\n']
    """
    chars = []
    i = start + 1
    quoted_style = _class_contains_quoted_items(pattern, start)

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

        # En clases estilo ['a' 'b' '\\n'], los espacios entre elementos son
        # separadores. El espacio literal se escribe como ' '.
        if quoted_style and pattern[i].isspace():
            i += 1
            continue

        left_chars, next_i = _read_class_atom(pattern, i)

        # Rango: a-z o 'a'-'z'. Solo se permite cuando cada lado es un carácter.
        if next_i < len(pattern) and pattern[next_i] == '-' and next_i + 1 < len(pattern) and pattern[next_i + 1] != ']':
            right_chars, after_right = _read_class_atom(pattern, next_i + 1)
            if len(left_chars) != 1 or len(right_chars) != 1:
                raise ValueError('Los rangos dentro de clases deben usar un carácter por lado.')
            a, b = left_chars[0], right_chars[0]
            if ord(a) > ord(b):
                raise ValueError(f'Rango inválido [{a}-{b}] en expresión regular.')
            for code in range(ord(a), ord(b) + 1):
                chars.append(chr(code))
            i = after_right
            continue

        chars.extend(left_chars)
        i = next_i

    raise ValueError('Clase de caracteres sin cerrar en expresión regular.')

# convierte la expresión regular en una lista de tokens (literales, operadores, paréntesis)
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
        elif c == "'":
            literal_chars, i = _read_quoted_literal(pattern, i)
            for ch in literal_chars:
                tokens.append(_literal(ch))
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

# dice si un token puede terminar un atomo de regex y devuelve true si es asi
def _can_end_atom(tok) -> bool:
    return _is_literal(tok) or tok == ')' or tok in {'*', '+', '?'}
# sirve para saber si hay que insertar una concatenacion 

# dice si un token puede iniciar un atomo de regex y devuelve true si es asi
def _can_start_atom(tok) -> bool:
    return _is_literal(tok) or tok == '('

# agrega concatenación explicita 
def add_concat(tokens):
    out = []
    for i, tok in enumerate(tokens):
        out.append(tok)
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if _can_end_atom(tok) and _can_start_atom(nxt):
                out.append(CONCAT)
    return out

#  convierte la regex a postfix
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

# construye un AFN  usando thomson y devuelve el estado inicial, el estado de aceptación y la tabla de transiciones
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

# recolecta todos los espados que aparecen en el AFN
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

# calcula la cerradura de epsilon
def epsilon_closure(states, trans):
    q, seen = deque(states), set(states)
    while q:
        state = q.popleft()
        for nxt in trans[state].get(EPS, set()):
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return frozenset(seen)