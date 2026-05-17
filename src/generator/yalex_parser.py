"""Parser mínimo para especificaciones YALex simplificadas."""
from .models import LexRule, YalSpec


def parse_yalex(path: str) -> YalSpec:
    rules = []
    with open(path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(None, 2)
            if len(parts) < 2:
                continue
            head = parts[0].upper()
            if head == 'IGNORE':
                token = parts[1]
                regex = parts[2] if len(parts) > 2 else parts[1]
                rules.append(LexRule(token, regex, True))
            elif head == 'TOKEN':
                token = parts[1]
                regex = parts[2] if len(parts) > 2 else ''
                rules.append(LexRule(token, regex, False))
    if not rules:
        raise ValueError('No se encontraron reglas válidas en .yal')
    return YalSpec(rules)
