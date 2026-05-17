"""Construcción y simulación de AFD para tokenización."""
from collections import defaultdict
from .regex_engine import tokenize_regex, add_concat, to_postfix, thompson, epsilon_closure, EPS


def build_dfa(spec):
    nfa_trans = defaultdict(lambda: defaultdict(set))
    start = 0
    next_state = 1
    accept_info = {}
    for idx, rule in enumerate(spec.rules):
        tokens = add_concat(tokenize_regex(rule.regex))
        (s, e), trans = thompson(to_postfix(tokens))
        offset = next_state
        for a in trans:
            for ch, bs in trans[a].items():
                for b in bs:
                    nfa_trans[a + offset][ch].add(b + offset)
        nfa_trans[start][EPS].add(s + offset)
        accept_info[e + offset] = (idx, rule.token, rule.ignore)
        next_state = max(next_state, max(trans.keys(), default=0) + offset + 1)

    alphabet = set()
    for a in nfa_trans:
        for ch in nfa_trans[a]:
            if ch != EPS:
                alphabet.add(ch)

    dfa_states = []
    dfa_map = {}
    dfa_trans = {}
    start_set = epsilon_closure({start}, nfa_trans)
    dfa_map[start_set] = 0
    dfa_states.append(start_set)
    i = 0
    while i < len(dfa_states):
        st = dfa_states[i]
        dfa_trans[i] = {}
        for ch in alphabet:
            nxt = set()
            for n in st:
                nxt.update(nfa_trans[n].get(ch, set()))
            if not nxt:
                continue
            c = epsilon_closure(nxt, nfa_trans)
            if c not in dfa_map:
                dfa_map[c] = len(dfa_states)
                dfa_states.append(c)
            dfa_trans[i][ch] = dfa_map[c]
        i += 1

    dfa_accept = {}
    for i, st in enumerate(dfa_states):
        candidates = [accept_info[s] for s in st if s in accept_info]
        if candidates:
            dfa_accept[i] = sorted(candidates, key=lambda x: x[0])[0]
    return {'trans': dfa_trans, 'accept': dfa_accept, 'start': 0}


def tokenize(text, dfa):
    i = 0
    out, errs = [], []
    while i < len(text):
        state, j = dfa['start'], i
        last = None
        while j < len(text) and text[j] in dfa['trans'].get(state, {}):
            state = dfa['trans'][state][text[j]]
            j += 1
            if state in dfa['accept']:
                last = (j, dfa['accept'][state])
        if last is None:
            errs.append(f'Error léxico en posición {i}: {repr(text[i])}')
            i += 1
            continue
        end, (_, token, ignore) = last
        lexeme = text[i:end]
        if not ignore:
            out.append((token, lexeme))
        i = end
    out.append(('$', '$'))
    return out, errs
