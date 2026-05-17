"""Parser de YAPar con secciones de tokens y producciones."""
from .models import Grammar


def _strip_comments(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] == '/' and text[i + 1] == '*':
            i += 2
            while i + 1 < len(text) and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)


def parse_yalp(path: str) -> Grammar:
    txt = _strip_comments(open(path, 'r', encoding='utf-8').read())
    if '%%' not in txt:
        raise ValueError('El archivo .yalp debe contener %%')
    tsec, psec = txt.split('%%', 1)
    terminals, ignore = set(), set()
    for line in tsec.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('%token'):
            for tok in s.split()[1:]:
                terminals.add(tok)
        elif s.startswith('IGNORE'):
            for tok in s.split()[1:]:
                ignore.add(tok)

    productions = {}
    chunks = psec.split(';')
    start = None
    for chunk in chunks:
        c = chunk.strip()
        if not c or ':' not in c:
            continue
        lhs, rhs_blob = c.split(':', 1)
        lhs = lhs.strip()
        if start is None:
            start = lhs
        alts = []
        for alt in rhs_blob.split('|'):
            seq = [x for x in alt.strip().split() if x]
            if seq:
                alts.append(seq)
        if alts:
            productions[lhs] = alts

    non_terminals = set(productions.keys())
    return Grammar(terminals, non_terminals, start, productions, ignore)
