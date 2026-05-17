"""Cálculo de FIRST y FOLLOW para gramáticas."""

def first_sets(grammar):
    first = {nt: set() for nt in grammar.non_terminals}
    changed = True
    while changed:
        changed = False
        for lhs, alts in grammar.productions.items():
            for rhs in alts:
                sym = rhs[0]
                add = {sym} if sym in grammar.terminals else first[sym]
                b = len(first[lhs])
                first[lhs].update(add - {'ε'})
                changed |= len(first[lhs]) != b
    return first


def follow_sets(grammar, first):
    follow = {nt: set() for nt in grammar.non_terminals}
    follow[grammar.start_symbol].add('$')
    changed = True
    while changed:
        changed = False
        for lhs, alts in grammar.productions.items():
            for rhs in alts:
                for i, b in enumerate(rhs):
                    if b not in grammar.non_terminals:
                        continue
                    trailer = rhs[i + 1:i + 2]
                    add = set()
                    if trailer:
                        t = trailer[0]
                        add = {t} if t in grammar.terminals else first[t]
                    else:
                        add = follow[lhs]
                    before = len(follow[b])
                    follow[b].update(add - {'ε'})
                    changed |= len(follow[b]) != before
    return follow
