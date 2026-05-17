"""Ejecuta los casos de prueba del proyecto.

Incluye:
- tres casos aceptados: low, medium y high;
- pruebas negativas oficiales: error léxico y error sintáctico.
"""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.dirname(__file__))
CASES = ['low', 'medium', 'high']
NEGATIVE_CASES = [
    {
        'name': 'low_lex_error',
        'base_case': 'low',
        'input_file': 'input_low_lex_error.txt',
        'expect_lex_error': True,
        'expect_syn_error': False,
    },
    {
        'name': 'low_syntax_error',
        'base_case': 'low',
        'input_file': 'input_low_syntax_error.txt',
        'expect_lex_error': False,
        'expect_syn_error': True,
    },
]


def case_paths(name):
    base = os.path.join(ROOT, 'tests_data', name)
    return {
        'yal':   os.path.join(base, f'lexer_{name}.yal'),
        'yalp':  os.path.join(base, f'parser_{name}.yalp'),
        'input': os.path.join(base, f'input_{name}.txt'),
        'out':   os.path.join(ROOT, 'outputs', f'{name}_test'),
    }


def negative_case_paths(case):
    base_name = case['base_case']
    base = os.path.join(ROOT, 'tests_data', base_name)
    return {
        'yal':   os.path.join(base, f'lexer_{base_name}.yal'),
        'yalp':  os.path.join(base, f'parser_{base_name}.yalp'),
        'input': os.path.join(base, case['input_file']),
        'out':   os.path.join(ROOT, 'outputs', f"{case['name']}_test"),
    }


def validate_paths(name, paths):
    """Verifica que los archivos de entrada existen antes de ejecutar."""
    missing = []
    for key in ('yal', 'yalp', 'input'):
        if not os.path.isfile(paths[key]):
            missing.append(f'  [{key}] {paths[key]}')
    if missing:
        print(f'  ERROR: faltan archivos para el caso "{name}":')
        for m in missing:
            print(m)
        return False
    return True


def run_generated(paths):
    generated_driver = os.path.join(paths['out'], 'run_generated.py')
    if not os.path.isfile(generated_driver):
        return None, 'run_generated.py no fue creado en la carpeta de salida.'

    generated = subprocess.run(
        [sys.executable, 'run_generated.py', paths['input']],
        cwd=paths['out'],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return generated, None


def run_positive_case(name, run):
    paths = case_paths(name)
    print(f'\n{"=" * 50}')
    print(f'  Caso aceptado: {name.upper()}')
    print(f'{"=" * 50}')

    if not validate_paths(name, paths):
        return 1

    try:
        result = run(paths['yal'], paths['yalp'], paths['input'], paths['out'])
    except Exception as exc:
        print(f'  ERROR en pipeline: {exc}')
        return 1

    failures = 0
    print(f"  Tokens reconocidos : {len(result['tokens'])}")

    if result['lex_errors']:
        failures += 1
        print('  Errores léxicos:')
        for error in result['lex_errors']:
            print('    ' + error)
    else:
        print('  Errores léxicos    : ninguno')

    if result['syn_error']:
        failures += 1
        print(f"  Error sintáctico   : {result['syn_error']}")
    else:
        print('  Error sintáctico   : ninguno')

    if not result['lex_errors'] and not result['syn_error']:
        print('  Resultado pipeline : ACEPTADO ✓')

    if result.get('warnings'):
        print('  Advertencias:')
        for w in result['warnings']:
            print('    ⚠ ' + w)

    generated, error = run_generated(paths)
    if error:
        print(f'  ERROR: {error}')
        failures += 1
    elif generated.returncode != 0:
        failures += 1
        print('  Analizador generado: FALLÓ (código de salida distinto de 0)')
        if generated.stdout:
            print('  stdout:', generated.stdout[:400])
        if generated.stderr:
            print('  stderr:', generated.stderr[:400])
    elif 'Resultado: cadena aceptada' not in generated.stdout:
        failures += 1
        print('  Analizador generado: FALLÓ (cadena no aceptada)')
        print('  stdout:', generated.stdout[:400])
        if generated.stderr:
            print('  stderr:', generated.stderr[:200])
    else:
        print('  Analizador generado: OK — independiente y funcional ✓')

    return failures


def run_negative_case(case, run):
    name = case['name']
    paths = negative_case_paths(case)
    print(f'\n{"=" * 50}')
    print(f'  Caso con error esperado: {name.upper()}')
    print(f'{"=" * 50}')

    if not validate_paths(name, paths):
        return 1

    try:
        result = run(paths['yal'], paths['yalp'], paths['input'], paths['out'])
    except Exception as exc:
        print(f'  ERROR inesperado en pipeline: {exc}')
        return 1

    failures = 0
    has_lex_error = bool(result['lex_errors'])
    has_syn_error = bool(result['syn_error'])

    print(f"  Tokens reconocidos : {len(result['tokens'])}")
    print(f"  Error léxico       : {'sí' if has_lex_error else 'no'}")
    print(f"  Error sintáctico   : {'sí' if has_syn_error else 'no'}")

    if case['expect_lex_error'] != has_lex_error:
        failures += 1
        print('  FALLÓ: el resultado léxico no coincide con lo esperado.')
    if case['expect_syn_error'] != has_syn_error:
        failures += 1
        print('  FALLÓ: el resultado sintáctico no coincide con lo esperado.')

    if result['lex_errors']:
        print('  Errores léxicos detectados:')
        for error in result['lex_errors']:
            print('    ' + error)
    if result['syn_error']:
        print('  Error sintáctico detectado:')
        print('    ' + result['syn_error'])

    generated, error = run_generated(paths)
    if error:
        print(f'  ERROR: {error}')
        failures += 1
    else:
        stdout = generated.stdout
        generated_has_lex = 'ERRORES LÉXICOS:' in stdout
        generated_has_syn = 'ERROR SINTÁCTICO:' in stdout
        if case['expect_lex_error'] != generated_has_lex:
            failures += 1
            print('  FALLÓ: el analizador generado no reportó el error léxico esperado.')
        if case['expect_syn_error'] != generated_has_syn:
            failures += 1
            print('  FALLÓ: el analizador generado no reportó el error sintáctico esperado.')
        if not failures:
            print('  Analizador generado: reportó el error esperado ✓')

    if not failures:
        print('  Resultado pipeline : error esperado detectado ✓')

    return failures


def main():
    # Asegura que src/ esté en el path para importar el generador.
    src_dir = os.path.join(ROOT, 'src')
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Import tardío para que sys.path esté configurado.
    try:
        from generator.pipeline import run
    except ImportError as e:
        print(f'ERROR: no se pudo importar el pipeline: {e}')
        print('  Asegúrate de ejecutar este script desde la raíz del proyecto.')
        print(f'  Raíz detectada: {ROOT}')
        sys.exit(1)

    failures = 0

    for name in CASES:
        failures += run_positive_case(name, run)

    for case in NEGATIVE_CASES:
        failures += run_negative_case(case, run)

    print(f'\n{"=" * 50}')
    if failures:
        print(f'  Resultado final: {failures} fallo(s). Revisa los errores arriba.')
        sys.exit(1)
    else:
        print('  Resultado final: todas las pruebas pasaron. ✓')


if __name__ == '__main__':
    main()