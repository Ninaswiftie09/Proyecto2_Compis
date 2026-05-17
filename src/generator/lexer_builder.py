"""Construcción y simulación de AFD para tokenización."""
from collections import defaultdict, deque
from .models import normalize_dfa
from .regex_engine import EPS, add_concat, all_states, epsilon_closure, thompson, to_postfix, tokenize_regex


def _copy_nfa_with_offset(target, source, offset):
    for src, row in source.items():
        for symbol, dests in row.items():
            for dest in dests:
                target[src + offset][symbol].add(dest + offset)


def build_dfa(spec):
    """Construye un AFD combinado desde todas las reglas léxicas.

    Se usa máximo avance. Si dos reglas aceptan el mismo lexema, gana la regla
    que apareció primero en el archivo .yal (menor priority).
    """
    nfa_trans = defaultdict(lambda: defaultdict(set))
    combined_start = 0
    next_state = 1
    accept_info = {}

    for priority, rule in enumerate(spec.rules):
        regex_tokens = add_concat(tokenize_regex(rule.regex))
        (start, end), trans = thompson(to_postfix(regex_tokens))
        states = all_states(trans, start, end)
        offset = next_state
        _copy_nfa_with_offset(nfa_trans, trans, offset)
        nfa_trans[combined_start][EPS].add(start + offset)
        accept_info[end + offset] = {
            'priority': priority,
            'token':    rule.token,
            'ignore':   rule.ignore,
        }
        next_state += max(states) + 1

    alphabet = sorted(
        symbol
        for row in nfa_trans.values()
        for symbol in row.keys()
        if symbol != EPS
    )

    start_set = epsilon_closure({combined_start}, nfa_trans)
    dfa_states = [start_set]
    dfa_map = {start_set: 0}
    dfa_trans = {}
    queue = deque([start_set])

    while queue:
        current = queue.popleft()
        current_id = dfa_map[current]
        dfa_trans[current_id] = {}
        for symbol in alphabet:
            move = set()
            for nfa_state in current:
                move.update(nfa_trans[nfa_state].get(symbol, set()))
            if not move:
                continue
            closed = epsilon_closure(move, nfa_trans)
            if closed not in dfa_map:
                dfa_map[closed] = len(dfa_states)
                dfa_states.append(closed)
                queue.append(closed)
            dfa_trans[current_id][symbol] = dfa_map[closed]

    dfa_accept = {}
    for dfa_id, nfa_set in enumerate(dfa_states):
        candidates = [accept_info[state] for state in nfa_set if state in accept_info]
        if candidates:
            dfa_accept[dfa_id] = min(candidates, key=lambda item: item['priority'])

    return {
        'start':        0,
        'trans':        dfa_trans,
        'accept':       dfa_accept,
        'ignore_tokens': sorted({rule.token for rule in spec.rules if rule.ignore}),
    }


def apply_ignore_tokens(dfa, ignore_tokens):
    """Marca como ignorados los tokens declarados con IGNORE en YAPar."""
    dfa = normalize_dfa(dfa)
    combined = set(dfa.get('ignore_tokens', set())) | set(ignore_tokens or [])
    for info in dfa['accept'].values():
        if info['token'] in combined:
            info['ignore'] = True
    dfa['ignore_tokens'] = sorted(combined)
    return dfa


def _position_from_index(text: str, index: int):
    """Calcula (línea, columna) para un índice en el texto.
    Pre-construye la tabla una sola vez para ser O(n) total."""
    line, col = 1, 1
    for pos, ch in enumerate(text):
        if pos == index:
            break
        if ch == '\n':
            line += 1
            col = 1
        else:
            col += 1
    return line, col


def _build_line_offsets(text: str):
    """Devuelve lista de offsets de inicio de cada línea (índice 0 = línea 1)."""
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == '\n' and i + 1 < len(text):
            offsets.append(i + 1)
    return offsets


def _offset_to_line_col(offsets, index):
    """Búsqueda binaria sobre offsets para obtener (línea, columna) en O(log n)."""
    lo, hi = 0, len(offsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offsets[mid] <= index:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1, index - offsets[lo] + 1


def tokenize(text: str, dfa: dict):
    """Tokeniza texto usando el DFA dado. Reporta errores léxicos con posición."""
    dfa = normalize_dfa(dfa)
    offsets = _build_line_offsets(text)   # O(n) una sola vez
    i = 0
    out = []
    errors = []

    while i < len(text):
        state = dfa['start']
        j = i
        last_accept = None

        while j < len(text):
            row = dfa['trans'].get(state, {})
            ch = text[j]
            if ch not in row:
                break
            state = row[ch]
            j += 1
            if state in dfa['accept']:
                last_accept = (j, dfa['accept'][state])

        if last_accept is None:
            line, col = _offset_to_line_col(offsets, i)
            errors.append(
                f"Error léxico en línea {line}, columna {col}: carácter {text[i]!r}"
            )
            i += 1
            continue

        end, info = last_accept
        lexeme = text[i:end]
        ignore = info.get('ignore', False) or info.get('token') in dfa.get('ignore_tokens', set())
        if not ignore:
            out.append((info['token'], lexeme))
        i = end

    out.append(('$', '$'))
    return out, errors


def dfa_to_text(dfa):
    dfa = normalize_dfa(dfa)
    lines = []
    lines.append(f"Estado inicial: {dfa['start']}")
    lines.append('Estados de aceptación:')
    for state in sorted(dfa['accept']):
        info = dfa['accept'][state]
        label = info['token'] + (' [IGNORE]' if info.get('ignore') else '')
        lines.append(f'  {state}: {label}')
    lines.append('Transiciones:')
    for state in sorted(dfa['trans']):
        for symbol in sorted(dfa['trans'][state]):
            display = symbol.encode('unicode_escape').decode('ascii')
            lines.append(f'  {state} -- {display!r} --> {dfa["trans"][state][symbol]}')
    return '\n'.join(lines) + '\n'


def dfa_to_dot(dfa):
    dfa = normalize_dfa(dfa)
    lines = [
        'digraph DFA {',
        '  rankdir=LR;',
        '  node [shape=circle];',
        '  start [shape=point];',
        f'  start -> {dfa["start"]};',
    ]
    for state, info in sorted(dfa['accept'].items()):
        label = f"{state}\\n{info['token']}"
        if info.get('ignore'):
            label += '\\nIGNORE'
        lines.append(f'  {state} [shape=doublecircle, label="{label}"];')
    for state, row in sorted(dfa['trans'].items()):
        for symbol, dest in sorted(row.items()):
            label = symbol.replace('\\', '\\\\').replace('"', '\\"')
            label = label.encode('unicode_escape').decode('ascii')
            lines.append(f'  {state} -> {dest} [label="{label}"];')
    lines.append('}')
    return '\n'.join(lines) + '\n'