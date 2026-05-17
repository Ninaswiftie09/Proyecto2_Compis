"""Parser para especificaciones YALex simplificadas y estilo Yacc/YALex.

Formatos aceptados:
1. Simplificado para el proyecto:
   TOKEN NUM [0-9]+
   IGNORE WS [ \t\n]+
2. Definiciones tipo YALex:
   let digit = [0-9]
   rule tokens = parse
     | digit+ { return NUM }
     | [' ' '\t' '\n']+ { return WS }

La lectura se hace sin usar librerías de expresiones regulares.
"""
from .models import LexRule, YalSpec


def _strip_comments(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] == '/' and text[i + 1] == '*':
            i += 2
            while i + 1 < len(text) and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            if i + 1 >= len(text):
                raise ValueError('Comentario /* ... */ sin cerrar en archivo .yal')
            i += 2
        elif i + 1 < len(text) and text[i] == '/' and text[i + 1] == '/':
            while i < len(text) and text[i] != '\n':
                i += 1
        elif text[i] == '#':
            while i < len(text) and text[i] != '\n':
                i += 1
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)


def _split_once_keyword(line: str, keyword: str):
    low = line.lower()
    key = keyword.lower()
    if not low.startswith(key):
        return None
    if len(line) > len(keyword) and not line[len(keyword)].isspace():
        return None
    return line[len(keyword):].strip()


def _parse_action_token(action: str):
    """Extrae el token desde una acción { return TOKEN } o { TOKEN }."""
    clean = action.strip()
    for ch in '{}();':
        clean = clean.replace(ch, ' ')
    parts = [p for p in clean.split() if p]
    if not parts:
        return None, True
    lowered = [p.lower() for p in parts]
    if 'return' in lowered:
        idx = lowered.index('return')
        if idx + 1 < len(parts):
            value = parts[idx + 1]
            if value.lower() in {'none', 'null', 'ignore', 'skip'}:
                return value.upper(), True
            return value, False
    value = parts[-1]
    if value.lower() in {'none', 'null', 'ignore', 'skip'}:
        return value.upper(), True
    return value, False


def _extract_rule_line(line: str):
    """Extrae regex y acción de una línea tipo | regex { return TOKEN }."""
    s = line.strip()
    if not s.startswith('|'):
        return None
    s = s[1:].strip()
    open_idx = s.find('{')
    close_idx = s.rfind('}')
    if open_idx == -1 or close_idx == -1 or close_idx < open_idx:
        return None
    regex = s[:open_idx].strip()
    action = s[open_idx + 1:close_idx].strip()
    token, ignore = _parse_action_token(action)
    if not token:
        return None
    return token, regex, ignore


def _replace_definitions(regex: str, definitions: dict) -> str:
    """Reemplaza nombres definidos con let por su regex entre paréntesis."""
    if not definitions:
        return regex
    result = []
    i = 0
    while i < len(regex):
        c = regex[i]
        if c == '\\':
            if i + 1 < len(regex):
                result.append(regex[i:i + 2])
                i += 2
            else:
                result.append(c)
                i += 1
        elif c.isalpha() or c == '_':
            j = i + 1
            while j < len(regex) and (regex[j].isalnum() or regex[j] == '_'):
                j += 1
            name = regex[i:j]
            if name in definitions:
                result.append('(' + definitions[name] + ')')
            else:
                result.append(name)
            i = j
        else:
            result.append(c)
            i += 1
    return ''.join(result)


def parse_yalex(path: str) -> YalSpec:
    text = _strip_comments(open(path, 'r', encoding='utf-8').read())
    rules = []
    definitions = {}
    warnings = []

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        let_body = _split_once_keyword(line, 'let')
        if let_body and '=' in let_body:
            name, value = let_body.split('=', 1)
            name = name.strip()
            value = value.strip()
            if not name:
                raise ValueError(f'Línea {line_no}: definición let sin nombre.')
            definitions[name] = _replace_definitions(value, definitions)
            continue

        token_body = _split_once_keyword(line, 'TOKEN')
        if token_body:
            parts = token_body.split(None, 1)
            if len(parts) != 2:
                raise ValueError(f'Línea {line_no}: TOKEN debe tener nombre y regex.')
            token, regex = parts[0], parts[1]
            rules.append(LexRule(token, _replace_definitions(regex, definitions), False, line_no))
            continue

        ignore_body = _split_once_keyword(line, 'IGNORE')
        if ignore_body:
            parts = ignore_body.split(None, 1)
            if len(parts) == 1:
                token, regex = parts[0], parts[0]
            else:
                token, regex = parts[0], parts[1]
            rules.append(LexRule(token, _replace_definitions(regex, definitions), True, line_no))
            continue

        yacc_rule = _extract_rule_line(line)
        if yacc_rule:
            token, regex, ignore = yacc_rule
            rules.append(LexRule(token, _replace_definitions(regex, definitions), ignore, line_no))
            continue

        if line.lower().startswith('rule ') or line.lower() in {'{', '}'}:
            continue

        warnings.append(f'Línea {line_no} ignorada por el parser YALex: {line}')

    if not rules:
        raise ValueError('No se encontraron reglas léxicas válidas en el archivo .yal')

    seen = set()
    for rule in rules:
        if not rule.token:
            raise ValueError(f'Línea {rule.source_line}: token sin nombre.')
        if rule.token in seen:
            warnings.append(f'Token {rule.token} aparece más de una vez; se usará prioridad por orden de aparición.')
        seen.add(rule.token)

    return YalSpec(rules=rules, definitions=definitions, warnings=warnings)
