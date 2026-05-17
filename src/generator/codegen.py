"""Generación de código Python independiente para lexer y parser."""
import json


def write_generated_lexer(path, dfa):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('DFA = ' + json.dumps(dfa) + '\n')
        f.write('def tokenize(text):\n')
        f.write(' from src.generator.lexer_builder import tokenize as _t\n')
        f.write(' return _t(text, DFA)\n')


def write_generated_parser(path, action, goto):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('ACTION = ' + json.dumps(action) + '\n')
        f.write('GOTO = ' + json.dumps(goto) + '\n')
        f.write('def parse(tokens):\n')
        f.write(' from src.generator.slr_builder import parse_tokens as _p\n')
        f.write(' return _p(tokens, ACTION, GOTO)\n')
