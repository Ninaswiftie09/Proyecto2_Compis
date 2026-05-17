"""Cálculo robusto de FIRST y FOLLOW para gramáticas libres de contexto."""
from .models import EPSILON, ENDMARK


def first_of_sequence(sequence, first, terminals):
    if not sequence:
        return {EPSILON}
    result = set()
    for symbol in sequence:
        if symbol in terminals or symbol == ENDMARK:
            result.add(symbol)
            return result
        symbol_first = first.get(symbol, set())
        result.update(symbol_first - {EPSILON})
        if EPSILON not in symbol_first:
            return result
    result.add(EPSILON)
    return result


def first_sets(grammar):
    first = {nt: set() for nt in grammar.non_terminals}
    changed = True
    while changed:
        changed = False
        for lhs, alternatives in grammar.productions.items():
            for rhs in alternatives:
                before = len(first[lhs])
                first[lhs].update(first_of_sequence(rhs, first, grammar.terminals))
                if len(first[lhs]) != before:
                    changed = True
    return first


def follow_sets(grammar, first):
    follow = {nt: set() for nt in grammar.non_terminals}
    follow[grammar.start_symbol].add(ENDMARK)
    changed = True
    while changed:
        changed = False
        for lhs, alternatives in grammar.productions.items():
            for rhs in alternatives:
                for i, symbol in enumerate(rhs):
                    if symbol not in grammar.non_terminals:
                        continue
                    beta = rhs[i + 1:]
                    first_beta = first_of_sequence(beta, first, grammar.terminals)
                    before = len(follow[symbol])
                    follow[symbol].update(first_beta - {EPSILON})
                    if EPSILON in first_beta:
                        follow[symbol].update(follow[lhs])
                    if len(follow[symbol]) != before:
                        changed = True
    return follow
