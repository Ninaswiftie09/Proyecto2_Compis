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


def tokenize_stream(text):
    """Generador que produce tokens uno a la vez desde el texto de entrada.

    Yields:
        ('LEX_ERROR', mensaje)  cuando hay un carácter no reconocido.
        (token, lexema)         para cada token reconocido (no ignorado).
        ('$', '$')              al final del texto.
    """
    dfa = _normalize_dfa(DFA)
    i = 0
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
            yield ('LEX_ERROR', f"Error léxico en línea {line}, columna {col}: carácter {text[i]!r}")
            i += 1
            continue
        end, info = last_accept
        lexeme = text[i:end]
        ignore = info.get('ignore', False) or info.get('token') in dfa.get('ignore_tokens', set())
        if not ignore:
            yield (info['token'], lexeme)
        i = end
    yield ('$', '$')


def tokenize(text):
    """Tokeniza el texto completo de una vez. Retorna (lista_tokens, lista_errores)."""
    tokens = []
    errors = []
    for item in tokenize_stream(text):
        tok, lex = item
        if tok == 'LEX_ERROR':
            errors.append(lex)
        else:
            tokens.append((tok, lex))
    return tokens, errors
''')


def write_generated_parser(path, action, goto):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(GENERATED_HEADER)
        f.write('ACTION = ' + repr(action) + '\n')
        f.write('GOTO = ' + repr(goto) + '\n\n')
        f.write(r'''
def _format_stack(stack):
    return ' '.join(str(x) for x in stack)


def _expected_tokens(action, state):
    return sorted(action.get(state, {}).keys())


def parse(token_stream):
    """Parsea leyendo tokens uno a la vez desde token_stream.

    token_stream debe ser un iterable que genere tuplas (token, lexema).
    Los tokens ('LEX_ERROR', mensaje) son recolectados como errores léxicos
    y se continúa solicitando el siguiente token al lexer.

    Retorna (trace, lex_errors, syn_error).
    """
    lex_errors = []
    stack = [0]
    trace = []
    _it = iter(token_stream)

    def _advance():
        """Solicita el siguiente token al lexer, uno a la vez."""
        while True:
            try:
                tok, lex = next(_it)
            except StopIteration:
                return '$', '$'
            if tok == 'LEX_ERROR':
                lex_errors.append(lex)
                continue
            return tok, lex

    current_token, current_lexeme = _advance()

    while True:
        state = stack[-1]
        act = ACTION.get(state, {}).get(current_token)
        if act is None:
            expected = ', '.join(_expected_tokens(ACTION, state)) or 'ningún token válido'
            return trace, lex_errors, (
                f'Error sintáctico en token {current_token!r} con lexema {current_lexeme!r}. '
                f'Estado {state}. Se esperaba: {expected}.'
            )
        if act[0] == 's':
            next_state = act[1]
            trace.append({
                'stack': _format_stack(stack),
                'input': current_token,
                'action': f'shift {current_token} -> {next_state}',
            })
            stack.append(next_state)
            current_token, current_lexeme = _advance()
        elif act[0] == 'r':
            lhs, rhs = act[1]
            trace.append({
                'stack': _format_stack(stack),
                'input': current_token,
                'action': f'reduce {lhs} -> {" ".join(rhs) if rhs else "ε"}',
            })
            for _ in range(len(rhs)):
                if len(stack) <= 1:
                    return trace, lex_errors, 'Error interno del parser: pila insuficiente durante una reducción.'
                stack.pop()
            goto_state = GOTO.get(stack[-1], {}).get(lhs)
            if goto_state is None:
                return trace, lex_errors, f'Error interno del parser: no existe GOTO[{stack[-1]}][{lhs}].'
            stack.append(goto_state)
        elif act[0] == 'acc':
            trace.append({
                'stack': _format_stack(stack),
                'input': current_token,
                'action': 'accept',
            })
            return trace, lex_errors, None
        else:
            return trace, lex_errors, f'Acción desconocida en tabla ACTION: {act}'
''')


def write_generated_driver(path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(GENERATED_HEADER)
        f.write(r'''import argparse
from generated_lexer import tokenize_stream
from generated_parser import parse


def main():
    ap = argparse.ArgumentParser(description='Analizador generado independiente')
    ap.add_argument('input', help='Archivo de texto plano a analizar')
    args = ap.parse_args()
    text = open(args.input, 'r', encoding='utf-8').read()

    # El parser solicita tokens al lexer uno a la vez a través del stream.
    stream = tokenize_stream(text)
    trace, lex_errors, syn_error = parse(stream)

    if lex_errors:
        print('ERRORES LÉXICOS:')
        for error in lex_errors:
            print('  ' + error)

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
