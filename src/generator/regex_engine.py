"""Motor de regex, basado en Thompson."""
from collections import defaultdict, deque

EPS = 'ε'


def tokenize_regex(pattern: str):
    tokens = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == '\\' and i + 1 < len(pattern):
            tokens.append('L:' + pattern[i + 1])
            i += 2
        elif c in '()*+?|':
            tokens.append(c)
            i += 1
        else:
            tokens.append(c)
            i += 1
    return tokens


def add_concat(tokens):
    out = []
    for i, t in enumerate(tokens):
        out.append(t)
        if i + 1 < len(tokens):
            a, b = t, tokens[i + 1]
            if (a not in '(|' and b not in ')|*+?'):
                out.append('.')
    return out


def to_postfix(tokens):
    prec = {'|': 1, '.': 2, '?': 3, '*': 3, '+': 3}
    out, stack = [], []
    for t in tokens:
        if t == '(':
            stack.append(t)
        elif t == ')':
            while stack and stack[-1] != '(':
                out.append(stack.pop())
            stack.pop()
        elif t in prec:
            while stack and stack[-1] != '(' and prec.get(stack[-1], 0) >= prec[t]:
                out.append(stack.pop())
            stack.append(t)
        else:
            out.append(t)
    while stack:
        out.append(stack.pop())
    return out


def thompson(postfix):
    next_state = 0
    trans = defaultdict(lambda: defaultdict(set))

    def ns():
        nonlocal next_state
        s = next_state
        next_state += 1
        return s

    stack = []
    for t in postfix:
        if t not in '.|*+?':
            a, b = ns(), ns()
            sym = t[2:] if t.startswith('L:') else t
            trans[a][sym].add(b)
            stack.append((a, b))
        elif t == '.':
            a1, b1 = stack.pop(-2)
            a2, b2 = stack.pop()
            trans[b1][EPS].add(a2)
            stack.append((a1, b2))
        elif t == '|':
            a1, b1 = stack.pop(-2)
            a2, b2 = stack.pop()
            s, e = ns(), ns()
            trans[s][EPS].update({a1, a2})
            trans[b1][EPS].add(e)
            trans[b2][EPS].add(e)
            stack.append((s, e))
        elif t == '*':
            a, b = stack.pop()
            s, e = ns(), ns()
            trans[s][EPS].update({a, e})
            trans[b][EPS].update({a, e})
            stack.append((s, e))
        elif t == '+':
            a, b = stack.pop()
            s, e = ns(), ns()
            trans[s][EPS].add(a)
            trans[b][EPS].update({a, e})
            stack.append((s, e))
        elif t == '?':
            a, b = stack.pop()
            s, e = ns(), ns()
            trans[s][EPS].update({a, e})
            trans[b][EPS].add(e)
            stack.append((s, e))
    return stack[-1], trans


def epsilon_closure(states, trans):
    q, seen = deque(states), set(states)
    while q:
        s = q.popleft()
        for t in trans[s].get(EPS, set()):
            if t not in seen:
                seen.add(t)
                q.append(t)
    return frozenset(seen)
