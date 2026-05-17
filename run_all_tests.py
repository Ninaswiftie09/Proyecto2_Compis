"""Ejecuta los tres casos de prueba del proyecto."""
import os
import subprocess
import sys
from src.generator.pipeline import run

ROOT = os.path.abspath(os.path.dirname(__file__))
CASES = ['low', 'medium', 'high']


def case_paths(name):
    base = os.path.join(ROOT, 'tests_data', name)
    return {
        'yal': os.path.join(base, f'lexer_{name}.yal'),
        'yalp': os.path.join(base, f'parser_{name}.yalp'),
        'input': os.path.join(base, f'input_{name}.txt'),
        'out': os.path.join(ROOT, 'outputs', f'{name}_test'),
    }


def main():
    failures = 0
    for name in CASES:
        paths = case_paths(name)
        print(f'\n=== Caso {name} ===')
        result = run(paths['yal'], paths['yalp'], paths['input'], paths['out'])
        print(f"Tokens reconocidos: {len(result['tokens'])}")
        if result['lex_errors']:
            failures += 1
            print('Errores léxicos:')
            for error in result['lex_errors']:
                print('  ' + error)
        if result['syn_error']:
            failures += 1
            print('Error sintáctico:', result['syn_error'])
        if not result['lex_errors'] and not result['syn_error']:
            print('Análisis aceptado.')

        generated = subprocess.run(
            [sys.executable, 'run_generated.py', paths['input']],
            cwd=paths['out'],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if generated.returncode != 0 or 'Resultado: cadena aceptada' not in generated.stdout:
            failures += 1
            print('Falló la ejecución independiente del analizador generado.')
            print(generated.stdout)
            print(generated.stderr)
        else:
            print('Analizador generado independiente: OK')

    if failures:
        print(f'\nResultado final: {failures} fallo(s).')
        sys.exit(1)
    print('\nResultado final: todas las pruebas pasaron.')


if __name__ == '__main__':
    main()
