"""Pipeline de generación y ejecución de análisis."""
import argparse
import os
from .yalex_parser import parse_yalex
from .lexer_builder import build_dfa, tokenize
from .yalp_parser import parse_yalp
from .slr_builder import build_slr, parse_tokens
from .codegen import write_generated_lexer, write_generated_parser


def run(yal, yalp, input_file, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    spec = parse_yalex(yal)
    dfa = build_dfa(spec)
    grammar = parse_yalp(yalp)
    C, trans, action, goto = build_slr(grammar)

    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    tokens, lex_errors = tokenize(text, dfa)
    trace, syn_error = parse_tokens(tokens, action, goto) if not lex_errors else ([], None)

    write_generated_lexer(os.path.join(out_dir, 'generated_lexer.py'), dfa)
    write_generated_parser(os.path.join(out_dir, 'generated_parser.py'), action, goto)

    with open(os.path.join(out_dir, 'dfa_transitions.txt'), 'w', encoding='utf-8') as f:
        for s, row in dfa['trans'].items():
            for ch, d in row.items():
                f.write(f'{s} --{repr(ch)}--> {d}\n')
    with open(os.path.join(out_dir, 'lr0_automaton.txt'), 'w', encoding='utf-8') as f:
        for i, I in enumerate(C):
            f.write(f'I{i}\n')
            for it in I:
                rhs = list(it.rhs)
                rhs.insert(it.dot, '•')
                f.write('  ' + it.lhs + ' -> ' + ' '.join(rhs) + '\n')
            for sym, j in trans.get(i, {}).items():
                f.write(f'  goto({sym})=I{j}\n')

    return {'tokens': tokens, 'lex_errors': lex_errors, 'trace': trace, 'syn_error': syn_error}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--yal', required=True)
    ap.add_argument('--yalp', required=True)
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    result = run(args.yal, args.yalp, args.input, args.out)
    print('TOKENS:', result['tokens'])
    print('LEX ERRORS:', result['lex_errors'])
    print('TRACE:', result['trace'])
    print('SYN ERROR:', result['syn_error'])
