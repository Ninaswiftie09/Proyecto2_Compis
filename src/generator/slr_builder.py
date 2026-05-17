"""Construcción de colección LR(0) y tabla SLR."""
from .models import Item
from .grammar_tools import first_sets, follow_sets


def closure(items, g):
    c = set(items)
    changed = True
    while changed:
        changed = False
        for it in list(c):
            sym = it.next_symbol()
            if sym in g.non_terminals:
                for rhs in g.productions[sym]:
                    ni = Item(sym, tuple(rhs), 0)
                    if ni not in c:
                        c.add(ni)
                        changed = True
    return frozenset(c)


def goto(items, sym, g):
    moved = [it.advance() for it in items if it.next_symbol() == sym]
    return closure(moved, g) if moved else frozenset()


def build_slr(grammar):
    aug = grammar.start_symbol + "'"
    grammar.non_terminals.add(aug)
    grammar.productions[aug] = [[grammar.start_symbol]]
    start = closure([Item(aug, (grammar.start_symbol,), 0)], grammar)
    C, idx = [start], {start: 0}
    trans = {}
    i = 0
    symbols = list(grammar.terminals | grammar.non_terminals)
    while i < len(C):
        I = C[i]
        trans[i] = {}
        for s in symbols:
            J = goto(I, s, grammar)
            if J:
                if J not in idx:
                    idx[J] = len(C)
                    C.append(J)
                trans[i][s] = idx[J]
        i += 1
    first = first_sets(grammar)
    follow = follow_sets(grammar, first)
    action, go = {}, {}
    for i, I in enumerate(C):
        action[i], go[i] = {}, {}
        for it in I:
            a = it.next_symbol()
            if a in grammar.terminals and a in trans[i]:
                action[i][a] = ('s', trans[i][a])
            elif a is None:
                if it.lhs == aug:
                    action[i]['$'] = ('acc', 0)
                else:
                    for f in follow[it.lhs]:
                        action[i][f] = ('r', (it.lhs, list(it.rhs)))
        for A in grammar.non_terminals:
            if A in trans[i]:
                go[i][A] = trans[i][A]
    return C, trans, action, go


def parse_tokens(tokens, action, go):
    stack = [0]
    idx = 0
    trace = []
    while True:
        st = stack[-1]
        tok = tokens[idx][0]
        act = action.get(st, {}).get(tok)
        if act is None:
            return trace, f'Error sintáctico en token {tokens[idx]}'
        if act[0] == 's':
            trace.append(f'shift {tok} -> {act[1]}')
            stack.append(act[1])
            idx += 1
        elif act[0] == 'r':
            lhs, rhs = act[1]
            trace.append(f'reduce {lhs} -> {" ".join(rhs)}')
            for _ in rhs:
                stack.pop()
            stack.append(go[stack[-1]][lhs])
        else:
            trace.append('accept')
            return trace, None
