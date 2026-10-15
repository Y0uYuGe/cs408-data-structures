"""Boolean grammar: NOT > AND > OR; adjacent operands imply AND."""
import re
from .structures import Stack

LEXER = re.compile(r'\s*("[^"\\]*"|\(|\)|[^\s()"]+)')
PRECEDENCE = {"OR": 1, "AND": 2, "NOT": 3}


def parse(expression):
    raw, position = [], 0
    while position < len(expression):
        if expression[position:].isspace():
            break
        match = LEXER.match(expression, position)
        if not match:
            raise ValueError("invalid query or unclosed quotation")
        raw.append(match.group(1)); position = match.end()
    if not raw:
        raise ValueError("empty query")
    tokens, previous_end = [], False
    for token in raw:
        starts = token not in ("AND", "OR", ")")
        if previous_end and starts:
            tokens.append("AND")
        tokens.append(token)
        previous_end = token == ")" or token not in PRECEDENCE and token != "("
    output, operators, expecting = [], Stack(), True
    for token in tokens:
        if token == "(":
            operators.push(token); expecting = True
        elif token == ")":
            if expecting:
                raise ValueError("missing operand")
            while operators and operators.peek() != "(":
                output.append(operators.pop())
            if not operators:
                raise ValueError("unmatched closing parenthesis")
            operators.pop(); expecting = False
        elif token in PRECEDENCE:
            if (token != "NOT" and expecting) or (token == "NOT" and not expecting):
                raise ValueError("misplaced operator")
            while operators and operators.peek() != "(" and (PRECEDENCE[operators.peek()] > PRECEDENCE[token] or token != "NOT" and PRECEDENCE[operators.peek()] == PRECEDENCE[token]):
                output.append(operators.pop())
            operators.push(token); expecting = True
        else:
            if not expecting:
                raise ValueError("missing operator")
            output.append(token); expecting = False
    if expecting:
        raise ValueError("query ends before an operand")
    while operators:
        token = operators.pop()
        if token == "(":
            raise ValueError("unmatched opening parenthesis")
        output.append(token)
    return output


def combine(a, b, operation):
    """Merge two ordered unique posting lists without a built-in set operation."""
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            if operation in ("AND", "OR"):
                out.append(a[i])
            i += 1; j += 1
        elif a[i] < b[j]:
            if operation in ("OR", "DIFF"):
                out.append(a[i])
            i += 1
        else:
            if operation == "OR":
                out.append(b[j])
            j += 1
    if operation in ("OR", "DIFF"):
        out.extend(a[i:])
    if operation == "OR":
        out.extend(b[j:])
    return out
