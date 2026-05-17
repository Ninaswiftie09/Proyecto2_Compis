"""Generación de código Python autocontenido para lexer y parser."""

GENERATED_HEADER = '''# Archivo generado automáticamente por el sistema.
# No depende del generador original para ejecutarse.

'''


def write_generated_lexer(path, dfa):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(GENERATED_HEADER)
        f.write('DFA = ' + repr(dfa) + '\n\n')
        f.write(r'''
def _normalize_dfa(dfa):
    trans = {}
    for state, row in dfa.get('trans', {}).items():
        trans[int(state)] = {symbol: int(dest) for symbol, dest in row.items()}
    accept = {}
    for state, info in dfa.get('accept', {}).items():
        if isinstance(info, dict):
            accept[int(state)] = {
                'priority': int(info.get('priority', 0)),
                'token': info.get('token'),
                'ignore': bool(info.get('ignore', False)),
            }
        else:
            priority, token, ignore = info
            accept[int(state)] = {'priority': int(priority), 'token': token, 'ignore': bool(ignore)}
    return {
        'start': int(dfa.get('start', 0)),
        'trans': trans,
        'accept': accept,
        'ignore_tokens': set(dfa.get('ignore_tokens', [])),
    }


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


def tokenize(text):
    dfa = _normalize_dfa(DFA)
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
''')


def write_generated_parser(path, action, goto):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(GENERATED_HEADER)
        f.write('ACTION = ' + repr(action) + '\n')
        f.write('GOTO = ' + repr(goto) + '\n\n')
        f.write(r'''
def _format_stack(stack):
    return ' '.join(str(x) for x in stack)


def _format_input(tokens, index):
    return ' '.join(tok for tok, _ in tokens[index:])


def _expected_tokens(action, state):
    return sorted(action.get(state, {}).keys())


def parse(tokens):
    if not tokens or tokens[-1][0] != '$':
        tokens = list(tokens) + [('$', '$')]
    stack = [0]
    index = 0
    trace = []
    while True:
        state = stack[-1]
        current_token = tokens[index][0] if index < len(tokens) else '$'
        act = ACTION.get(state, {}).get(current_token)
        if act is None:
            expected = ', '.join(_expected_tokens(ACTION, state)) or 'ningún token válido'
            lexeme = tokens[index][1] if index < len(tokens) else '$'
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
            trace.append({
                'stack': _format_stack(stack),
                'input': _format_input(tokens, index),
                'action': f'reduce {lhs} -> {" ".join(rhs) if rhs else "ε"}',
            })
            for _ in range(len(rhs)):
                if len(stack) <= 1:
                    return trace, 'Error interno del parser: pila insuficiente durante una reducción.'
                stack.pop()
            goto_state = GOTO.get(stack[-1], {}).get(lhs)
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
''')


def write_generated_driver(path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(GENERATED_HEADER)
        f.write(r'''import argparse
from generated_lexer import tokenize
from generated_parser import parse


def main():
    ap = argparse.ArgumentParser(description='Analizador generado independiente')
    ap.add_argument('input', help='Archivo de texto plano a analizar')
    args = ap.parse_args()
    text = open(args.input, 'r', encoding='utf-8').read()
    tokens, lex_errors = tokenize(text)
    print('TOKENS:')
    for token, lexeme in tokens:
        print(f'  {token}: {lexeme!r}')
    if lex_errors:
        print('\nERRORES LÉXICOS:')
        for error in lex_errors:
            print('  ' + error)
        return
    trace, syn_error = parse(tokens)
    print('\nTRAZA SINTÁCTICA:')
    for row in trace:
        print(f"  stack=[{row['stack']}] input=[{row['input']}] action={row['action']}")
    if syn_error:
        print('\nERROR SINTÁCTICO:')
        print('  ' + syn_error)
    else:
        print('\nResultado: cadena aceptada')


if __name__ == '__main__':
    main()
''')
