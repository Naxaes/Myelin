from dataclasses import dataclass
from typing import Optional
from lexer import Token


TERMINATORS  = 'br', 'jmp', 'ret'
SIDE_EFFECTS = 'ret', 'print', 'call', 'alloc', 'free'


@dataclass
class Code:
    op:    str
    type:  Optional[str] = None  # Inferred type
    dest:  Optional[str] = None
    args:  tuple = ()               # Contains some data; numbers, labels, and things that aren't references
    refs:  tuple = ()               # Contains a reference to an instruction in code
    token: Optional[Token] = None



def c(**kwargs):
    op = kwargs.pop('op')

    if op in ("add", 'sub', 'mul', 'gt', 'lt', 'get'):
        a, b = kwargs.pop('refs')
        type = kwargs.pop('type', None)
        dest = kwargs.pop('dest')
        assert not kwargs
        return Code(op, type=type, dest=dest, refs=(a, b))
    if op == "lit":
        a, *_ = kwargs.pop('args'); assert not _
        type = kwargs.pop('type', None)
        dest = kwargs.pop('dest')
        assert not kwargs
        return Code(op, type=type, dest=dest, args=(int(a),))
    if op == "print":
        refs = kwargs.pop('refs')
        type = kwargs.pop('type', None)
        assert not kwargs
        return Code(op, type=type, refs=refs)
    if op in ('ref', 'move', 'alloc'):
        a, *_ = kwargs.pop('refs'); assert not _
        type = kwargs.pop('type', None)
        dest = kwargs.pop('dest')
        assert not kwargs
        return Code(op, type=type, dest=dest, refs=(a,))
    if op in "br":
        c, *_ = kwargs.pop('refs'); assert not _
        l, r = kwargs.pop('args')
        type = kwargs.pop('type', None)
        assert not kwargs
        return Code(op, type=type, args=(l, r), refs=(c, ))
    if op == 'jmp':
        a, *_ = kwargs.pop('args'); assert not _
        assert not kwargs
        return Code(op, args=(a,))
    if op == 'ret':
        refs = kwargs.pop('refs', tuple())
        assert not kwargs
        return Code(op, refs=refs)
    if op == 'set':
        obj, idx, val = kwargs.pop('refs')
        type = kwargs.pop('type', None)
        assert not kwargs
        return Code(op, type=type, refs=(obj, idx, val))

    assert False, f'{op}, {kwargs}'