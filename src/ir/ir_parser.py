from typing import Optional
from collections import namedtuple
from ir.basic_block import Block
from ir.function import Function
from ir.ir import Op, Code
from ir.module import Module, Builtin


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
    while source and (source[0] == ' ' or source[0] == '\t' or source.startswith('#')):
        source, _ = parse_filter(source, lambda x: x == ' ' or x == '\t')
        if source.startswith('#'):
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


def parse(source: str):
    functions = {
        'alloc': Builtin('alloc', [('memory',  'ptr')], {'size':  ('int', 0)}),
        'print': Builtin('print', [('written', 'int')], {'value': (None, 0)})
    }
    function: Optional[Function] = None
    block: Optional[Block] = None
    data = {}

    terminators_to_patch = {}

    while True:
        if source[0].isspace():
            source = source[1:]
        elif source[0] == '#':
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

            function = Function(name.repr, args)

        # Parse label
        elif token.repr == '$':
            assert function is not None
            source, label = parse_token(source)  # Some labels are keywords... FIX!
            source, _ = parse_token(source, expect_kind='end')

            block = Block(label.repr)
            function.add(block)

        # Parse NOP
        elif token.kind == 'ident' and token.repr == 'nop':
            source, _ = parse_token(source, expect_kind='end')
            block.add(Code(Op.NOP))

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
                match arg_or_op.repr:
                    case 'ref':
                        block.add(Code(Op.REF, dest=dest, refs=(arg.repr, )))
                    case 'move':
                        block.add(Code(Op.MOVE, dest=dest, refs=(arg.repr, )))
                    case 'alloc':
                        block.add(Code(Op.ALLOC, dest=dest, refs=(arg.repr, )))
                    case _:
                        raise RuntimeError(f'Unknown operator {arg_or_op.repr}')
            elif arg_or_op.kind == 'ident':
                source, op   = parse_token(source)
                source, arg2 = parse_token(source, expect_kind='ident')
                source, _    = parse_token(source, expect_kind='end')
                if op.repr in OPERATORS:
                    op = Op[OPERATORS[op.repr].upper()]
                    block.add(Code(op, dest=dest, refs=(arg_or_op.repr, arg2.repr)))
                elif op.repr == 'get':
                    block.add(Code(Op.GET, dest=dest, refs=(arg_or_op.repr, arg2.repr)))
                elif arg_or_op.repr == 'call':
                    block.add(Code(Op.CALL, dest=dest, args=(op.repr, ), refs=(arg2.repr, )))
                else:
                    raise RuntimeError(f'Unknown operator {op.repr}')
            elif arg_or_op.kind == 'number':
                source, _ = parse_token(source, expect_kind='end')
                value = int(arg_or_op.repr)
                index = len(data)
                data[index] = value
                block.add(Code(Op.LIT, dest=dest, args=('int', index, value)))
            else:
                raise RuntimeError(f'Expected kind ident, got {arg_or_op.kind} ({arg_or_op.repr})')

        elif token.kind == 'keyword':
            op = token.repr
            if op in ('print', 'free'):
                source, arg = parse_token(source, expect_kind='ident')
                source, _   = parse_token(source, expect_kind='end')
                match op:
                    case 'print':
                        block.add(Code(Op.PRINT, refs=(arg.repr, )))
                    case 'free':
                        block.add(Code(Op.FREE, refs=(arg.repr, )))
                    case _:
                        raise RuntimeError(f'Unknown keyword {op}')
            elif op == 'ret':
                arg = ()
                try:
                    source, _   = parse_token(source, expect_kind='end')
                except RuntimeError:
                    source, arg = parse_token(source, expect_kind='ident')
                    source, _ = parse_token(source, expect_kind='end')
                    arg = (arg, )
                block.terminator = Code(Op.RET, refs=arg)
            elif op == 'jmp':
                source, _   = parse_token(source, expect_repr='$')
                source, arg = parse_token(source)  # Some labels are keywords... FIX!
                source, _   = parse_token(source, expect_kind='end')
                terminators_to_patch[block.label] = block, Code(Op.JMP), arg.repr
            elif op == 'br':
                source, cond  = parse_token(source, expect_kind='ident')
                source, _     = parse_token(source, expect_repr='$')
                source, left  = parse_token(source)  # Some labels are keywords... FIX!
                source, _     = parse_token(source, expect_repr='$')
                source, right = parse_token(source)  # Some labels are keywords... FIX!
                source, _     = parse_token(source, expect_kind='end')
                terminators_to_patch[block.label] = block, Code(Op.BR), cond.repr, left.repr, right.repr
            elif op == 'set':
                source, obj    = parse_token(source, expect_kind='ident')
                source, offset = parse_token(source, expect_kind='ident')
                source, value  = parse_token(source, expect_kind='ident')
                source, _      = parse_token(source, expect_kind='end')
                block.add(Code(Op.SET, refs=(obj.repr, offset.repr, value.repr)))
            elif op == 'end':
                source, _ = parse_token(source, expect_kind='end')
                for label, (block, terminator, *args) in terminators_to_patch.items():
                    match terminator.op:
                        case Op.JMP:
                            dst = next(i for i, b in enumerate(function.blocks) if b.label == args[0])
                            block.terminator = Code(terminator.op, args=(dst, ))
                        case Op.BR:
                            left = next(i for i, b in enumerate(function.blocks) if b.label == args[1])
                            right = next(i for i, b in enumerate(function.blocks) if b.label == args[2])
                            block.terminator = Code(terminator.op, refs=(args[0], ), args=(left, right))
                        case _:
                            raise RuntimeError(f'Unknown terminator {terminator.op}')

                functions[function.name] = function
                function = None
        else:
            assert False, f"Unhandled token {token}"

        source, token = parse_token(source)

    if function is not None:
        print("Missing 'end'")
        exit(1)

    return Module('module', functions, data, {}, {}, {})
