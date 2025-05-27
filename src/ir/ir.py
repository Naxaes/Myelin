from dataclasses import dataclass
from typing import Optional
from lexer import Token


TERMINATORS  = 'br', 'jmp', 'ret', 'leave'
SIDE_EFFECTS = 'ret', 'print', 'call', 'alloc', 'free', 'syscall', 'decl', 'multidecl', 'asm'
ARITHMETICS = '+', '-', '*', '/', '%'
LOGICALS = 'and', 'or', 'not', '==', '!=', '>', '<', '>=', '<='
INSTRUCTIONS = ARITHMETICS + LOGICALS + ('.', 'as', 'index', 'assign', 'get', 'lit', 'ref', 'move', 'param', 'field', 'init') + SIDE_EFFECTS + TERMINATORS





@dataclass
class Code:
    op:    str
    dest:  Optional[str] = None
    args:  tuple = ()               # Contains some data; numbers, labels, types, and things that aren't references
    refs:  tuple = ()               # Contains a reference to an instruction in code
    token: Optional[Token] = None

    def lhs(self): return self.refs[0]
    def rhs(self): return self.refs[1]
    def expr(self): return self.refs[1]
    def obj(self): return self.refs[0]
    def attr(self): return self.refs[1]
    def target(self): return self.refs[0]
    def type(self): return self.args[0] if self.args else None



def c(**kwargs):
    op = kwargs.pop('op')
    assert op in INSTRUCTIONS

    if op in ("add", 'sub', 'mul', 'gt', 'lt', 'get'):
        a, b = kwargs.pop('refs')
        dest = kwargs.pop('dest')
        assert not kwargs
        return Code(op, dest=dest, refs=(a, b))
    if op == "lit":
        a, *_ = kwargs.pop('args'); assert not _
        dest = kwargs.pop('dest')
        assert not kwargs
        return Code(op, dest=dest, args=(int(a),))
    if op == "print":
        refs = kwargs.pop('refs')
        assert not kwargs
        return Code(op, refs=refs)
    if op in ('ref', 'move', 'alloc'):
        a, *_ = kwargs.pop('refs'); assert not _
        dest = kwargs.pop('dest')
        assert not kwargs
        return Code(op, dest=dest, refs=(a,))
    if op in "br":
        c, *_ = kwargs.pop('refs'); assert not _
        l, r = kwargs.pop('args')
        assert not kwargs
        return Code(op, args=(l, r), refs=(c, ))
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
        assert not kwargs
        return Code(op, refs=(obj, idx, val))

    assert False, f'{op}, {kwargs}'