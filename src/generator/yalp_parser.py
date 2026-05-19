"""Parser de YAPar con sección de tokens, IGNORE y producciones."""
from .models import EPSILON, Grammar

# elimina comentarios del archvio yalp
def _strip_comments(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] == '/' and text[i + 1] == '*':
            i += 2
            while i + 1 < len(text) and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            if i + 1 >= len(text):
                raise ValueError('Comentario /* ... */ sin cerrar en archivo .yalp')
            i += 2
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)

# determina si un simbolo parece token (mayusculas y al menos una letra)
def _is_token_name(symbol: str) -> bool:
    return symbol == symbol.upper() and any(ch.isalpha() for ch in symbol)


def parse_yalp(path: str) -> Grammar:
    txt = _strip_comments(open(path, 'r', encoding='utf-8').read())
    # verifica que exista %% para separar tokens y producciones
    if '%%' not in txt:
        raise ValueError('El archivo .yalp debe contener %% para separar tokens y producciones.')
    # separa las secciones de tokens y producciones usando el primer %% como separador
    token_section, production_section = txt.split('%%', 1)

    terminals = set()
    ignore = set()
    warnings = []

    # procesa los tokens y los tokens a ignorar, validando que tengan formato correcto y guardando advertencias sobre mayúsculas o tokens ignorados no declarados
    for line_no, raw in enumerate(token_section.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        head = parts[0]
        if head == '%token' or head.lower() == 'token':
            if len(parts) == 1:
                raise ValueError(f'Línea {line_no}: declaración de token sin nombres.')
            for tok in parts[1:]:
                terminals.add(tok)
                if tok != tok.upper():
                    warnings.append(f'Línea {line_no}: el token {tok} no está en mayúsculas.')
        elif head == 'IGNORE':
            if len(parts) == 1:
                raise ValueError(f'Línea {line_no}: IGNORE debe indicar al menos un token.')
            for tok in parts[1:]:
                ignore.add(tok)
                terminals.add(tok)
        else:
            raise ValueError(f'Línea {line_no}: contenido inválido en sección de tokens: {line}')

    #  valida que existan terminales 
    if not terminals:
        raise ValueError('La primera sección del .yalp debe declarar tokens con %token.')

    # procesa las producciones, detecta el símbolo de inicio y valida que los símbolos usados estén declarados
    productions = {}
    start = None
    absolute_line_offset = len(token_section.splitlines()) + 1
    chunks = production_section.split(';')
    for chunk in chunks:
        if not chunk.strip():
            continue
        if ':' not in chunk:
            raise ValueError(f'Producción inválida, falta dos puntos (:): {chunk.strip()}')
        lhs, rhs_blob = chunk.split(':', 1)
        lhs = lhs.strip()
        if not lhs:
            raise ValueError('Producción sin nombre en el lado izquierdo.')
        if _is_token_name(lhs):
            warnings.append(f'El lado izquierdo {lhs} parece token; los no terminales deberían escribirse en minúscula.')
        #detecta el simbolo incial
        if start is None:
            start = lhs
        alternatives = []
        for alt in rhs_blob.split('|'):
            seq = [x for x in alt.strip().split() if x]
            # maneja epsilon
            if not seq or seq == [EPSILON] or seq == ['epsilon']:
                alternatives.append([])
            else:
                alternatives.append(seq)
        if lhs in productions:
            productions[lhs].extend(alternatives)
        else:
            productions[lhs] = alternatives

    if not productions or start is None:
        raise ValueError('No se encontraron producciones válidas en el archivo .yalp')

    # valida simbolos usados
    non_terminals = set(productions.keys())
    for lhs, alts in productions.items():
        for rhs in alts:
            for sym in rhs:
                if sym in terminals or sym in non_terminals:
                    continue
                # si parece token pero no es
                if _is_token_name(sym):
                    raise ValueError(f'El token {sym} se usa en producciones pero no fue declarado con %token.')
                raise ValueError(f'El no terminal {sym} se usa en producciones pero no tiene producción propia.')

    undeclared_ignored = ignore - terminals
    if undeclared_ignored:
        warnings.append('Tokens en IGNORE agregados a terminales: ' + ', '.join(sorted(undeclared_ignored)))

    return Grammar(
        terminals=terminals,
        non_terminals=non_terminals,
        start_symbol=start,
        productions=productions,
        ignore_tokens=ignore,
        warnings=warnings,
    )
