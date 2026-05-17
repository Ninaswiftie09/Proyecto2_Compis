"""Ejecuta los tres casos de prueba del proyecto."""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.dirname(__file__))
CASES = ['low', 'medium', 'high']


def case_paths(name):
    base = os.path.join(ROOT, 'tests_data', name)
    return {
        'yal':   os.path.join(base, f'lexer_{name}.yal'),
        'yalp':  os.path.join(base, f'parser_{name}.yalp'),
        'input': os.path.join(base, f'input_{name}.txt'),
        'out':   os.path.join(ROOT, 'outputs', f'{name}_test'),
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


def main():
    # Asegura que src/ esté en el path para importar el generador
    src_dir = os.path.join(ROOT, 'src')
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Import tardío para que sys.path esté configurado
    try:
        from generator.pipeline import run
    except ImportError as e:
        print(f'ERROR: no se pudo importar el pipeline: {e}')
        print(f'  Asegúrate de ejecutar este script desde la raíz del proyecto.')
        print(f'  Raíz detectada: {ROOT}')
        sys.exit(1)

    failures = 0

    for name in CASES:
        paths = case_paths(name)
        print(f'\n{"=" * 50}')
        print(f'  Caso: {name.upper()}')
        print(f'{"=" * 50}')

        # Validar archivos antes de continuar
        if not validate_paths(name, paths):
            failures += 1
            continue

        # Ejecutar pipeline principal
        try:
            result = run(paths['yal'], paths['yalp'], paths['input'], paths['out'])
        except Exception as exc:
            print(f'  ERROR en pipeline: {exc}')
            failures += 1
            continue

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

        # Verificar que el analizador generado es independiente y funciona
        generated_driver = os.path.join(paths['out'], 'run_generated.py')
        if not os.path.isfile(generated_driver):
            print('  ERROR: run_generated.py no fue creado en la carpeta de salida.')
            failures += 1
            continue

        generated = subprocess.run(
            [sys.executable, 'run_generated.py', paths['input']],
            cwd=paths['out'],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if generated.returncode != 0:
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

    print(f'\n{"=" * 50}')
    if failures:
        print(f'  Resultado final: {failures} fallo(s). Revisa los errores arriba.')
        sys.exit(1)
    else:
        print('  Resultado final: todas las pruebas pasaron. ✓')


if __name__ == '__main__':
    main()