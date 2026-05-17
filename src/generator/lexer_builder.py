"""Construcción y simulación de AFD para tokenización."""
from collections import defaultdict, deque
from .regex_engine import EPS, add_concat, all_states, epsilon_closure, thompson, to_postfix, tokenize_regex


def _copy_nfa_with_offset(target, source, offset):
    for src, row in source.items():
        for symbol, dests in row.items():
            for dest in dests:
                target[src + offset][symbol].add(dest + offset)


def _normalize_dfa(dfa):
    """Convierte tablas cargadas desde JSON a enteros cuando haga falta."""
    trans = {}
    for state, row in dfa.get('trans', {}).items():
        state_i = int(state)
        trans[state_i] = {symbol: int(dest) for symbol, dest in row.items()}
    accept = {}
    for state, info in dfa.get('accept', {}).items():
        state_i = int(state)
        if isinstance(info, dict):
            accept[state_i] = {
                'priority': int(info.get('priority', 0)),
                'token': info.get('token'),
                'ignore': bool(info.get('ignore', False)),
            }
        else:
            priority, token, ignore = info
            accept[state_i] = {'priority': int(priority), 'token': token, 'ignore': bool(ignore)}
    return {
        'start': int(dfa.get('start', 0)),
        'trans': trans,
        'accept': accept,
        'ignore_tokens': set(dfa.get('ignore_tokens', [])),
    }


def build_dfa(spec):
    """Construye un AFD combinado desde todas las reglas léxicas.

    Se usa máximo avance. Si dos reglas aceptan el mismo lexema, gana la regla
    que apareció primero en el archivo .yal.
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
            'token': rule.token,
            'ignore': rule.ignore,
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
        'start': 0,
        'trans': dfa_trans,
        'accept': dfa_accept,
        'ignore_tokens': sorted({rule.token for rule in spec.rules if rule.ignore}),
    }


def apply_ignore_tokens(dfa, ignore_tokens):
    """Marca como ignorados los tokens declarados con IGNORE en YAPar."""
    dfa = _normalize_dfa(dfa)
    combined = set(dfa.get('ignore_tokens', set())) | set(ignore_tokens or [])
    for info in dfa['accept'].values():
        if info['token'] in combined:
            info['ignore'] = True
    dfa['ignore_tokens'] = sorted(combined)
    return dfa


def _position_from_index(text, index):
    line = 1
    col = 1
    for pos, ch in enumerate(text):
        if pos == index:
            break
        if ch == '\n':
            line += 1
            col = 1
        else:
            col += 1
    return line, col


def tokenize(text, dfa):
    dfa = _normalize_dfa(dfa)
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
            line, col = _position_from_index(text, i)
            errors.append(f"Error léxico en línea {line}, columna {col}: carácter {text[i]!r}")
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
    dfa = _normalize_dfa(dfa)
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
    dfa = _normalize_dfa(dfa)
    lines = ['digraph DFA {', '  rankdir=LR;', '  node [shape=circle];', '  start [shape=point];', f'  start -> {dfa["start"]};']
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
