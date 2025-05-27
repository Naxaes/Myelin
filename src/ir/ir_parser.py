from typing import Optional
from collections import namedtuple
from collections  import OrderedDict
from ir.basic_block import Block
from ir.ir import TERMINATORS, Op

KEYWORDS = {
    'jmp',
    'print',
    'ret',
    'free',
    'br',
    'set',
    'get',
    'end',
    'ref',
    'move',
    'alloc',
}
OPERATORS = {
   '+': 'add',
   '-': 'sub',
   '*': 'mul',
   '/': 'div',
   '%': 'mod',
   '>': 'gt',
   '>=': 'ge',
   '<': 'lt',
   '==': 'eq',
   '!=': 'ne',
}

Token = namedtuple('Token', ('kind', 'repr'))

def parse_filter(s_: str, f):
    i = 0
    while i < len(s_) and f(s_[i]):
        i += 1
    return s_[i:], s_[:i]

def skip(source: str) -> str:
    while source and (source[0] == ' ' or source[0] == '\t' or source.startswith('//')):
        source, _ = parse_filter(source, lambda x: x == ' ' or x == '\t')
        if source.startswith('//'):
            source, _ = parse_filter(source, lambda x: x != '\n')
    return source


def parse_token(source: str, expect_kind: Optional[str] = None, expect_repr: Optional[str] = None) -> tuple[str, Token]:
    def token_or_throw(source_: str, kind_: str, repr_: str):
        if expect_kind and kind_ != expect_kind:
            raise RuntimeError(f'Expected kind {expect_kind}, got {kind_} ({repr_})')
        if expect_repr and repr_ != expect_repr:
            raise RuntimeError(f'Expected kind {expect_repr}, got {repr_}')
        return source_, Token(kind_, repr_)

    if not source:
        return source, Token('eof', source)

    # Skip whitespace and comments.
    source = skip(source)

    if not source:
        return source, Token('eof', source)

    c = source[0]
    if c == '\n':
        while True:
            if source and source[0].isspace():
                source = source[1:]
            else:
                return token_or_throw(source, 'end', '\n')
    elif c.isdigit():
        s, r = parse_filter(source, str.isdigit)
        return token_or_throw(s, 'number', int(r))
    elif c.isalpha() or c == '_':
        s, r = parse_filter(source, lambda x: x.isalpha() or x.isdigit() or x == '_' or x == '*')
        if r in KEYWORDS:
            return token_or_throw(s, 'keyword', r)
        else:
            return token_or_throw(s, 'ident', r)
    elif source[0:2] in OPERATORS:
        return token_or_throw(source[2:], 'operator', source[:2])
    elif source[0:1] in OPERATORS:
        return token_or_throw(source[1:], 'operator', source[:1])
    elif c in ('@', '$', ':', '='):
        return token_or_throw(source[1:], 'special', source[:1])
    elif source[0:1] in ('(', '[', '{', ')', ']', '}'):
        return token_or_throw(source[1:], 'parenthesis', source[:1])
    elif source[0:1] in (',', '.'):
        return token_or_throw(source[1:], 'period', source[:1])
    else:
        assert False, f'Unknown token: ' + c


def parse(source: str, program_args: list[str]):
    functions = []
    function: Optional[dict] = None
    instrs: Optional[list] = []

    while True:
        if source[0].isspace():
            source = source[1:]
        elif source[:2] == '//':
            source = skip(source)
        else:
            break


    source, token = parse_token(source)

    while token.kind != 'eof':
        # Parse function
        if token.repr == '@':
            source, name = parse_token(source, expect_kind='ident')
            source, _ = parse_token(source, expect_repr='(')

            args = []
            source, arg_or_paren = parse_token(source)
            while arg_or_paren.kind != 'parenthesis':
                source, colon = parse_token(source)
                if colon.repr == ':':
                    source, ty = parse_token(source, expect_kind='ident')
                    args.append({'name': arg_or_paren.repr, 'type': ty.repr})
                else:
                    assert False, 'Not implemented'
                source, comma_arg_or_paren = parse_token(source)
                if comma_arg_or_paren.repr == ',':
                    source, arg_or_paren = parse_token(source)
                else:
                    arg_or_paren = comma_arg_or_paren

            source, arrow_or_end = parse_token(source)
            if arrow_or_end.repr == '->':
                assert False, "Not implemented"
            assert arrow_or_end.kind == 'end'

            function = { 'name': name.repr, 'args': args, 'rets': ['void'], 'instrs': instrs }

        # Parse label
        elif token.repr == '$':
            assert function is not None
            source, label = parse_token(source)  # Some labels are keywords... FIX!
            source, _ = parse_token(source, expect_kind='end')
            instrs.append({ "label": label.repr })

        # Parse NOP
        elif token.kind == 'ident' and token.repr == 'nop':
            source, _ = parse_token(source, expect_kind='end')
            instrs.append({"op": 'nop', "type": None, "dest": None, "args": []})

        # Parse operator
        elif token.kind == 'ident':
            dest = token.repr
            source, colon = parse_token(source, expect_repr=':')
            source, equal_or_ty = parse_token(source)
            if equal_or_ty.repr == '=':
                ty = '?'
            elif equal_or_ty.kind == 'ident':
                source, _ = parse_token(source, expect_repr='=')
                ty = equal_or_ty.repr
            else:
                raise RuntimeError(f'Expected kind ident or ":", got {equal_or_ty.kind} ({equal_or_ty.repr})')

            source, arg_or_op = parse_token(source)
            if arg_or_op.repr in ('ref', 'move', 'alloc'):
                source, arg = parse_token(source, expect_kind='ident')
                source, _   = parse_token(source, expect_kind='end')
                instrs.append({"op": arg_or_op.repr, "type": ty, "dest": dest, "args": [arg.repr]})
            elif arg_or_op.kind == 'ident':
                source, op   = parse_token(source)
                source, arg2 = parse_token(source, expect_kind='ident')
                source, _    = parse_token(source, expect_kind='end')
                instrs.append({"op": op.repr, "type": ty, "dest": dest, "args": [arg_or_op.repr, arg2.repr]})
            elif arg_or_op.kind == 'number':
                source, _ = parse_token(source, expect_kind='end')
                instrs.append({"op": Op.LIT, "type": ty, "dest": dest, "args": [arg_or_op.repr]})
            else:
                raise RuntimeError(f'Expected kind ident, got {arg_or_op.kind} ({arg_or_op.repr})')

        elif token.kind == 'keyword':
            op = token.repr
            if op in ('print', 'free'):
                source, arg = parse_token(source, expect_kind='ident')
                source, _   = parse_token(source, expect_kind='end')
                instrs.append({"op": op, "args": [arg.repr]})
            elif op == 'ret':
                arg = []
                try:
                    source, _   = parse_token(source, expect_kind='end')
                except RuntimeError:
                    source, arg = parse_token(source, expect_kind='ident')
                    source, _ = parse_token(source, expect_kind='end')
                    arg = [arg]
                instrs.append({"op": op, "args": arg})
            elif op == 'jmp':
                source, _   = parse_token(source, expect_repr='$')
                source, arg = parse_token(source)  # Some labels are keywords... FIX!
                source, _   = parse_token(source, expect_kind='end')
                instrs.append({"op": op, "label": arg.repr})
            elif op == 'br':
                source, cond  = parse_token(source, expect_kind='ident')
                source, _     = parse_token(source, expect_repr='$')
                source, left  = parse_token(source)  # Some labels are keywords... FIX!
                source, _     = parse_token(source, expect_repr='$')
                source, right = parse_token(source)  # Some labels are keywords... FIX!
                source, _     = parse_token(source, expect_kind='end')
                instrs.append({ "op": "br", "true": left.repr, "false": right.repr, "args": [cond.repr]})
            elif op == 'set':
                source, obj    = parse_token(source, expect_kind='ident')
                source, offset = parse_token(source, expect_kind='ident')
                source, value  = parse_token(source, expect_kind='ident')
                source, _      = parse_token(source, expect_kind='end')
                instrs.append({"op": "set", "args": [obj.repr, offset.repr, value.repr]})
            elif op == 'end':
                source, _ = parse_token(source, expect_kind='end')
                functions.append(function)
                function = None
        else:
            assert False, f"Unhandled token {token}"

        source, token = parse_token(source)

    if function is not None:
        print("Missing 'end'")
        exit(1)

    return { 'args': program_args, 'functions': functions }



def map_to_basic_blocks(instructions: list[dict]) -> OrderedDict[str, Block]:
    out: OrderedDict[str, Block] = OrderedDict()

    label = 'entry'
    current = []
    definitions: set[str] = set()
    arguments: set[str] = set()

    for i, instruction in enumerate(instructions):
        if 'op' in instruction:
            current.append(instruction)

            if 'args' in instruction:
                arguments.update(x for x in instruction['args'] if type(x) == str and x not in definitions)

            if 'dest' in instruction:
                dest = instruction['dest']
                definitions.add(dest)

            if instruction['op'] in TERMINATORS:
                out[label] = Block(label, arguments, current)
                current = []
                definitions = set()
                arguments = set()
                label = f'block_{len(out)}'
        else:
            assert Op.LABEL in instruction
            if current:
                out[label] = Block(label, arguments, current)

            current = []
            definitions = set()
            arguments = set()
            label = instruction[Op.LABEL]

            # If there is an empty label at the end of the program, still create the block.
            if i+1 == len(instructions):
                out[label] = Block(label, arguments, current)

    if current:
        out[label] = Block(label, arguments, current)

    return out
#
#
# def build_cfg_from_block_map(block_map: OrderedDict[str, Block]) -> list[Block]:
#     for i, (name, block) in enumerate(block_map.items()):
#         last = block.terminator
#
#         if last['op'] == Op.BR:
#             left  = last['true']
#             right = last['false']
#             # block.successors = [block_map[left], block_map[right]]
#             # block_map[left].predecessors.append(block)
#             # block_map[right].predecessors.append(block)
#
#         elif last['op'] == Op.JMP:
#             label = last[Op.LABEL]
#             # block.successors = [block_map[label]]
#             # block_map[label].predecessors.append(block)
#
#         elif last['op'] == Op.RET:
#             pass
#             # block.successors = []
#
#         elif i < len(block_map) - 1:
#             next_block = block_map[list(block_map.keys())[i+1]]
#             # block.successors = [next_block]
#             # next_block.predecessors.append(block)
#
#     return list(block_map.values())


def build_cfg(instructions: list[dict]) -> tuple[list[Block], dict[str, list[Block]], dict[str, list[Block]]]:
    block_map = map_to_basic_blocks(instructions)

    predecessors: dict[str, list[Block]] = { b.label: [] for b in block_map.values() }
    successors: dict[str, list[Block]]   = { b.label: [] for b in block_map.values() }

    for i, (name, block) in enumerate(block_map.items()):
        last = block.terminator

        if last is None:
            continue

        elif last.op == Op.BR:
            cond, left, right = last.args

            successors[block.label] = [block_map[left], block_map[right]]
            predecessors[left].append(block)
            predecessors[right].append(block)

        elif last.op == Op.JMP:
            label = last.label
            successors[block.label] = [block_map[label]]
            predecessors[label].append(block)

        elif last.op == Op.RET:
            successors[block.label] = []

        elif i < len(block_map) - 1:
            next_block = block_map[list(block_map.keys())[i+1]]
            successors[block.label] = [next_block]
            predecessors[next_block.label].append(block)

    return list(block_map.values()), predecessors, successors





def parse_2(source: str, args: list[str]):
    """
    TODO: These needs to be updated!
    <function>      ::= '@' <ident> '(' <param>* ')' '{' <statement>* '}'

    <statement>     ::= <print> | <branch> | <jmp> | <label> | <declaration>
    <print>         ::= 'print' <ident>
    <branch>        ::= 'br' <ident> <ident> <ident>
    <jmp>           ::= 'jmp' <ident>
    <label>         ::= '$' [a-zA-Z]
    <declaration>   ::= <ident> ':' <type> '=' <expression>
                    |   <ident> ':=' <expression>

    <expression>    ::= <ident> <op> <ident>
                    |   <literal>
    """
    def try_cast_to_float(source: str) -> Optional[float]:
        try:
            return float(source)
        except ValueError:
            return None


    module: dict = {
        'args': args,
        'functions': []
    }

    function: Optional[dict] = None

    code = [x.split('//')[0] for x in source.split('\n')]
    code = [x.strip() for x in " ".join(code).split(' ') if x.strip()]
    i = 0
    while i < len(code):
        c = code[i]
        if c.startswith('@'):
            assert function is None
            name, args_ = c.split('(')

            if args_ != ')':
                args = [x.strip() for x in args_.split(',') if len(x.strip()) > 0]
                args[-1] = args[-1][:-1]
            else:
                args = []
            if code[i+1] == '->':
                rets = [code[i+2]]
                i += 2
            else:
                rets = ['void']


            function = {
                'name': name[1:],
                'args': args,
                'rets': rets,
                'instrs': []
            }
        elif c.startswith('end'):
            module['functions'].append(function)
            function = None
        elif c.startswith('$'):
            # Parse label
            assert function is not None
            function['instrs'].append({ "label": c[1:] })
        elif c.startswith('jmp'):
            i += 1
            lbl = code[i]
            assert lbl.startswith('$')
            assert function is not None
            function['instrs'].append({ "op": "jmp", "label": lbl[1:]})
        elif c.startswith('br'):
            cond, true, false = code[i+1], code[i+2], code[i+3]
            assert true.startswith('$') and false.startswith('$')
            i += 3
            assert function is not None
            function['instrs'].append({ "op": "br", "true": true[1:], "false": false[1:], "args": [cond]})
        elif c.startswith('print'):
            i += 1
            arg = code[i]
            assert function is not None
            function['instrs'].append({"op": "print", "args": [arg]})
        elif c.startswith('ret'):
            arg = []
            if code[i+1] not in ('$', '@') and code[i+1] != 'end':
                i += 1
                arg = [code[i]]
            assert function is not None
            function['instrs'].append({"op": "ret", "args": arg})
        elif c.startswith('free'):
            i += 1
            arg = code[i]
            assert function is not None
            function['instrs'].append({"op": "free", "args": [arg]})
        elif c.startswith('set'):
            obj, offset, val = code[i+1], code[i+2], code[i+3]
            i += 3
            assert function is not None
            function['instrs'].append({"op": "set", "args": [obj, offset, val]})
        else:
            # Parse instruction
            dest = code[i]
            type = '?'
            if code[i+1] == ':':
                i += 1
                type = code[i+1]
                i += 1
            elif code[i+1] != ':=':
                assert False, code[i+1]
            i += 2

            if code[i].isdigit() or (code[i].startswith('-') and code[i][1:].isdigit()):
                lit = code[i]
                assert function is not None
                function['instrs'].append({"op": "lit", "type": type, "dest": dest, "args": [int(lit)]})
            elif (lit := try_cast_to_float(code[i])) is not None:
                assert function is not None
                function['instrs'].append({"op": "lit", "type": type, "dest": dest, "args": [float(lit)]})
            elif code[i] == 'ref':
                i += 1
                arg = code[i]
                assert function is not None
                function['instrs'].append({"op": "ref", "type": type, "dest": dest, "args": [arg]})
            elif code[i] == 'move':
                i += 1
                arg = code[i]
                assert function is not None
                function['instrs'].append({"op": "move", "type": type, "dest": dest, "args": [arg]})
            elif code[i] == 'alloc':
                i += 1
                arg = code[i]
                assert function is not None
                function['instrs'].append({"op": "alloc", "type": type, "dest": dest, "args": [arg]})
            else:
                arg1, op, arg2 = code[i], code[i+1], code[i+2]
                i += 2

                if op == 'get':
                    assert function is not None
                    function['instrs'].append({ "op": "get", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '+':
                    assert function is not None
                    function['instrs'].append({ "op": "add", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '-':
                    assert function is not None
                    function['instrs'].append({ "op": "sub", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '*':
                    assert function is not None
                    function['instrs'].append({"op": "mul", "type": type, "dest": dest, "args": [arg1, arg2]})
                elif op == '/':
                    assert function is not None
                    function['instrs'].append({ "op": "div", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '%':
                    assert function is not None
                    function['instrs'].append({ "op": "mod", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '>':
                    assert function is not None
                    function['instrs'].append({ "op": "gt", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '>=':
                    assert function is not None
                    function['instrs'].append({ "op": "ge", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '==':
                    assert function is not None
                    function['instrs'].append({ "op": "eq", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '<=':
                    assert function is not None
                    function['instrs'].append({ "op": "le", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '<':
                    assert function is not None
                    function['instrs'].append({ "op": "lt", "type": type, "dest": dest, "args": [arg1, arg2] })
                elif op == '!=':
                    assert function is not None
                    function['instrs'].append({ "op": "ne", "type": type, "dest": dest, "args": [arg1, arg2] })
                else:
                    if arg1 == 'get': raise RuntimeError('get is an infix operator')
                    assert False, f'Unknown instruction: ' + op
        i += 1

    if function is not None:
        print("Missing 'end'")
        exit(1)
    return module
