"""Pipeline de generación y ejecución del lexer/parser SLR."""
import argparse
import os
import subprocess
from .codegen import write_generated_driver, write_generated_lexer, write_generated_parser
from .lexer_builder import apply_ignore_tokens, build_dfa, dfa_to_dot, dfa_to_text, tokenize
from .slr_builder import build_slr, lr0_to_dot, lr0_to_text, parse_tokens, table_to_text
from .yalex_parser import parse_yalex
from .yalp_parser import parse_yalp


def _write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def _try_render_dot(dot_path, png_path):
    """Renderiza con Graphviz si está disponible. Si no, deja el .dot listo."""
    try:
        subprocess.run(['dot', '-Tpng', dot_path, '-o', png_path], check=True, capture_output=True, timeout=8)
        return True
    except Exception:
        return False


def _validate_token_compatibility(spec, grammar):
    lexical_tokens = {rule.token for rule in spec.rules}
    missing_in_lexer = sorted(grammar.terminals - lexical_tokens)
    unused_in_parser = sorted((lexical_tokens - grammar.ignore_tokens) - grammar.terminals)
    warnings = []
    if missing_in_lexer:
        raise ValueError('Tokens declarados en YAPar pero no generados por YALex: ' + ', '.join(missing_in_lexer))
    if unused_in_parser:
        warnings.append('Tokens generados por YALex que no se usan en YAPar: ' + ', '.join(unused_in_parser))
    return warnings


def run(yal, yalp, input_file, out_dir):
    if not yal or not yalp or not input_file or not out_dir:
        raise ValueError('Debes indicar archivo .yal, archivo .yalp, archivo de entrada y carpeta de salida.')

    os.makedirs(out_dir, exist_ok=True)

    spec = parse_yalex(yal)
    grammar = parse_yalp(yalp)
    compatibility_warnings = _validate_token_compatibility(spec, grammar)

    dfa = build_dfa(spec)
    dfa = apply_ignore_tokens(dfa, grammar.ignore_tokens)

    collection, transitions, action, goto, conflicts, augmented = build_slr(grammar)
    if conflicts:
        conflict_text = '\n'.join(conflicts)
        raise ValueError('La gramática no es SLR(1) por conflictos:\n' + conflict_text)

    text = open(input_file, 'r', encoding='utf-8').read()
    tokens, lex_errors = tokenize(text, dfa)
    if lex_errors:
        trace, syn_error = [], 'No se ejecutó el parser porque existen errores léxicos.'
    else:
        trace, syn_error = parse_tokens(tokens, action, goto)

    lexer_path = os.path.join(out_dir, 'generated_lexer.py')
    parser_path = os.path.join(out_dir, 'generated_parser.py')
    driver_path = os.path.join(out_dir, 'run_generated.py')
    write_generated_lexer(lexer_path, dfa)
    write_generated_parser(parser_path, action, goto)
    write_generated_driver(driver_path)

    dfa_txt = os.path.join(out_dir, 'dfa_transitions.txt')
    dfa_dot = os.path.join(out_dir, 'dfa_transitions.dot')
    dfa_png = os.path.join(out_dir, 'dfa_transitions.png')
    lr0_txt = os.path.join(out_dir, 'lr0_automaton.txt')
    lr0_dot = os.path.join(out_dir, 'lr0_automaton.dot')
    lr0_png = os.path.join(out_dir, 'lr0_automaton.png')
    table_txt = os.path.join(out_dir, 'slr_table.txt')

    _write(dfa_txt, dfa_to_text(dfa))
    _write(dfa_dot, dfa_to_dot(dfa))
    _write(lr0_txt, lr0_to_text(collection, transitions))
    _write(lr0_dot, lr0_to_dot(collection, transitions))
    _write(table_txt, table_to_text(action, goto))

    rendered = {
        'dfa_png': _try_render_dot(dfa_dot, dfa_png),
        'lr0_png': _try_render_dot(lr0_dot, lr0_png),
    }

    warnings = []
    warnings.extend(spec.warnings)
    warnings.extend(grammar.warnings)
    warnings.extend(compatibility_warnings)
    if not rendered['dfa_png'] or not rendered['lr0_png']:
        warnings.append('Graphviz no está disponible; se dejaron archivos .dot para generar los PNG.')

    return {
        'tokens': tokens,
        'lex_errors': lex_errors,
        'trace': trace,
        'syn_error': syn_error,
        'warnings': warnings,
        'files': {
            'generated_lexer': lexer_path,
            'generated_parser': parser_path,
            'generated_driver': driver_path,
            'dfa_txt': dfa_txt,
            'dfa_dot': dfa_dot,
            'dfa_png': dfa_png if rendered['dfa_png'] else None,
            'lr0_txt': lr0_txt,
            'lr0_dot': lr0_dot,
            'lr0_png': lr0_png if rendered['lr0_png'] else None,
            'slr_table': table_txt,
        },
    }


def _print_result(result):
    print('TOKENS:')
    for token, lexeme in result['tokens']:
        print(f'  {token}: {lexeme!r}')
    print('\nERRORES LÉXICOS:')
    if result['lex_errors']:
        for error in result['lex_errors']:
            print('  ' + error)
    else:
        print('  Ninguno')
    print('\nTRAZA SINTÁCTICA:')
    if result['trace']:
        for row in result['trace']:
            print(f"  stack=[{row['stack']}] input=[{row['input']}] action={row['action']}")
    else:
        print('  Sin traza')
    print('\nERROR SINTÁCTICO:')
    print('  ' + str(result['syn_error'] or 'Ninguno'))
    if result['warnings']:
        print('\nADVERTENCIAS:')
        for warning in result['warnings']:
            print('  ' + warning)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Generador SLR para YALex + YAPar')
    ap.add_argument('--yal', required=True, help='Archivo YALex')
    ap.add_argument('--yalp', required=True, help='Archivo YAPar')
    ap.add_argument('--input', required=True, help='Archivo de texto plano a analizar')
    ap.add_argument('--out', required=True, help='Carpeta de salida')
    args = ap.parse_args()
    _print_result(run(args.yal, args.yalp, args.input, args.out))
