"""Construcción de colección LR(0), tabla SLR y ejecución del parser."""
from copy import deepcopy
from .grammar_tools import first_sets, follow_sets
from .models import ENDMARK, Item


def _sorted_items(items):
    return sorted(items, key=lambda it: (it.lhs, it.rhs, it.dot))

# calcula la cerradura de un conjunto de items LR(0)
def closure(items, grammar):
    result = set(items)
    changed = True
    while changed:
        changed = False
        for item in list(result):
            symbol = item.next_symbol()
            if symbol in grammar.non_terminals:
                for rhs in grammar.productions[symbol]:
                    new_item = Item(symbol, tuple(rhs), 0)
                    if new_item not in result:
                        result.add(new_item)
                        changed = True
    return frozenset(result)

# calcula a que estado se llega al avanzar con cierto simbolo (sirve para contruir las transiciones del automata LR(0))
def goto(items, symbol, grammar):
    advanced = [item.advance() for item in items if item.next_symbol() == symbol]
    return closure(advanced, grammar) if advanced else frozenset()

# inserta una accion en la tabla action y detecta conflictos SLR
def _set_action(action_table, state, terminal, value, conflicts):
    current = action_table.setdefault(state, {}).get(terminal)
    if current is not None and current != value:
        conflicts.append(f'Conflicto SLR en estado {state}, símbolo {terminal}: {current} vs {value}')
        # Se conserva la primera acción para no ocultar el conflicto.
        return
    action_table[state][terminal] = value

# aumenta la gramatica 
def _augment_grammar(grammar):
    g = deepcopy(grammar)
    aug = g.start_symbol + "'"
    while aug in g.non_terminals or aug in g.terminals:
        aug += "'"
    g.non_terminals.add(aug)
    g.productions[aug] = [[g.start_symbol]]
    g.start_symbol = aug
    return g, aug

# construye todo lo necesario para el parser SLR
def build_slr(grammar):
    """Retorna C, transiciones, ACTION, GOTO, conflictos y gramática aumentada."""
    augmented, augmented_start = _augment_grammar(grammar)
    initial_item = Item(augmented_start, tuple(augmented.productions[augmented_start][0]), 0)
    initial = closure([initial_item], augmented)

    collection = [initial]
    indexes = {initial: 0}
    transitions = {}
    symbols = sorted(augmented.terminals | augmented.non_terminals)
    i = 0
    while i < len(collection):
        state_items = collection[i]
        transitions[i] = {}
        for symbol in symbols:
            target = goto(state_items, symbol, augmented)
            if not target:
                continue
            if target not in indexes:
                indexes[target] = len(collection)
                collection.append(target)
            transitions[i][symbol] = indexes[target]
        i += 1

    first = first_sets(augmented)
    follow = follow_sets(augmented, first)
    action = {state: {} for state in range(len(collection))}
    go = {state: {} for state in range(len(collection))}
    conflicts = []

    for state_id, state_items in enumerate(collection):
        for item in _sorted_items(state_items):
            symbol = item.next_symbol()
            if symbol in augmented.terminals and symbol in transitions[state_id]:
                _set_action(action, state_id, symbol, ('s', transitions[state_id][symbol]), conflicts)
            elif symbol is None:
                if item.lhs == augmented_start:
                    _set_action(action, state_id, ENDMARK, ('acc', 0), conflicts)
                else:
                    for terminal in sorted(follow[item.lhs]):
                        _set_action(action, state_id, terminal, ('r', (item.lhs, list(item.rhs))), conflicts)
        for nt in sorted(augmented.non_terminals):
            if nt in transitions[state_id]:
                go[state_id][nt] = transitions[state_id][nt]

    return collection, transitions, action, go, conflicts, augmented


def _format_stack(stack):
    return ' '.join(str(x) for x in stack)


def _format_input(tokens, index):
    return ' '.join(tok for tok, _ in tokens[index:])


def _expected_tokens(action, state):
    return sorted(action.get(state, {}).keys())

#  ejecura el parser slr, usa una pila de estados y una lista de tokens, devuelve una traza de la ejecución y un mensaje de error si ocurre un error sintáctico
def parse_tokens(tokens, action, go):
    """Ejecuta análisis SLR sobre tokens [(TOKEN, lexema), ...]."""
    if not tokens or tokens[-1][0] != ENDMARK:
        tokens = list(tokens) + [(ENDMARK, ENDMARK)]

    stack = [0]
    index = 0
    trace = []

    while True:
        state = stack[-1]
        current_token = tokens[index][0] if index < len(tokens) else ENDMARK
        act = action.get(state, {}).get(current_token)

        if act is None:
            expected = ', '.join(_expected_tokens(action, state)) or 'ningún token válido'
            lexeme = tokens[index][1] if index < len(tokens) else ENDMARK
            return trace, (
                f'Error sintáctico en token {current_token!r} con lexema {lexeme!r}. '
                f'Estado {state}. Se esperaba: {expected}.'
            )

        if act[0] == 's':
            next_state = act[1]
            trace.append({
                'stack': _format_stack(stack),
                'input': _format_input(tokens, index),
                'action': f'shift {current_token} -> {next_state}',
            })
            stack.append(next_state)
            index += 1
        elif act[0] == 'r':
            lhs, rhs = act[1]
            rhs_len = len(rhs)
            trace.append({
                'stack': _format_stack(stack),
                'input': _format_input(tokens, index),
                'action': f'reduce {lhs} -> {" ".join(rhs) if rhs else "ε"}',
            })
            for _ in range(rhs_len):
                if len(stack) <= 1:
                    return trace, 'Error interno del parser: pila insuficiente durante una reducción.'
                stack.pop()
            goto_state = go.get(stack[-1], {}).get(lhs)
            if goto_state is None:
                return trace, f'Error interno del parser: no existe GOTO[{stack[-1]}][{lhs}].'
            stack.append(goto_state)
        elif act[0] == 'acc':
            trace.append({
                'stack': _format_stack(stack),
                'input': _format_input(tokens, index),
                'action': 'accept',
            })
            return trace, None
        else:
            return trace, f'Acción desconocida en tabla ACTION: {act}'

#  convierte el automata LR(0) a texto 
def lr0_to_text(collection, transitions):
    lines = []
    for idx, state_items in enumerate(collection):
        lines.append(f'I{idx}')
        for item in _sorted_items(state_items):
            rhs = list(item.rhs)
            rhs.insert(item.dot, '•')
            if not item.rhs:
                rhs = ['•', 'ε'] if item.dot == 0 else ['ε', '•']
            lines.append(f'  {item.lhs} -> {" ".join(rhs)}')
        for symbol, target in sorted(transitions.get(idx, {}).items()):
            lines.append(f'  goto({symbol}) = I{target}')
        lines.append('')
    return '\n'.join(lines)

# genea el .dot
def lr0_to_dot(collection, transitions):
    lines = ['digraph LR0 {', '  rankdir=LR;', '  node [shape=box, fontname="Courier"];']
    for idx, state_items in enumerate(collection):
        item_lines = []
        for item in _sorted_items(state_items):
            rhs = list(item.rhs)
            rhs.insert(item.dot, '•')
            if not item.rhs:
                rhs = ['•', 'ε']
            item_lines.append(f'{item.lhs} -> {" ".join(rhs)}')
        label = f'I{idx}\\n' + '\\n'.join(item_lines)
        label = label.replace('"', '\\"')
        lines.append(f'  I{idx} [label="{label}"];')
    for src, row in sorted(transitions.items()):
        for symbol, dest in sorted(row.items()):
            label = symbol.replace('"', '\\"')
            lines.append(f'  I{src} -> I{dest} [label="{label}"];')
    lines.append('}')
    return '\n'.join(lines) + '\n'

# genera la tabla slr en texto
def table_to_text(action, go):
    action_terms = sorted({term for row in action.values() for term in row})
    goto_terms = sorted({nt for row in go.values() for nt in row})
    lines = []
    lines.append('ACTION')
    header = ['state'] + action_terms
    lines.append('\t'.join(header))
    for state in sorted(action):
        row = [str(state)]
        for term in action_terms:
            act = action[state].get(term, '')
            if act:
                if act[0] == 's':
                    row.append(f's{act[1]}')
                elif act[0] == 'r':
                    lhs, rhs = act[1]
                    row.append(f'r({lhs}->{" ".join(rhs) if rhs else "ε"})')
                else:
                    row.append('acc')
            else:
                row.append('')
        lines.append('\t'.join(row))
    lines.append('')
    lines.append('GOTO')
    header = ['state'] + goto_terms
    lines.append('\t'.join(header))
    for state in sorted(go):
        row = [str(state)] + [str(go[state].get(nt, '')) for nt in goto_terms]
        lines.append('\t'.join(row))
    return '\n'.join(lines) + '\n'
