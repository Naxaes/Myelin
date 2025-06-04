from dataclasses import dataclass
from typing import Optional
from enum import Enum, auto

from lexer import Token


class Op(Enum):
    NOP = auto()
    # Arithmetic
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    # Logical
    AND = auto()
    OR = auto()
    NOT = auto()
    EQ = auto()
    NEQ = auto()
    GT = auto()
    LT = auto()
    GTE = auto()
    LTE = auto()
    # Misc
    DOT = auto()
    AS = auto()
    INDEX = auto()
    ASSIGN = auto()
    GET = auto()
    LIT = auto()
    BRW = auto()
    REF = auto()
    MOVE = auto()
    COPY = auto()
    PARAM = auto()
    FIELD = auto()
    INIT = auto()
    ACCESS = auto()
    # Side effects
    RET = auto()
    PRINT = auto()
    CALL = auto()
    ALLOC = auto()
    FREE = auto()
    SYSCALL = auto()
    DECL = auto()
    MULTIDECL = auto()
    ASM = auto()
    # Terminators
    BR = auto()
    JMP = auto()
    SET = auto()
    # Special
    _ = auto()
    LABEL = auto()

    def __str__(self):
        return self.name.lower()
    def __repr__(self):
        return self.name.lower()


TERMINATORS  = (Op.BR, Op.JMP, Op.RET)
SIDE_EFFECTS = (Op.RET, Op.PRINT, Op.CALL, Op.ALLOC, Op.FREE, Op.SYSCALL, Op.DECL, Op.MULTIDECL, Op.ASM)
ARITHMETICS = (Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD)
LOGICALS = (Op.AND, Op.OR, Op.NOT, Op.EQ, Op.NEQ, Op.GT, Op.LT, Op.GTE, Op.LTE)
INSTRUCTIONS = ARITHMETICS + LOGICALS + (
    Op.DOT, Op.AS, Op.INDEX, Op.ASSIGN, Op.GET, Op.LIT, Op.REF, Op.MOVE, Op.COPY, Op.BRW, Op.PARAM, Op.FIELD, Op.INIT
) + SIDE_EFFECTS + TERMINATORS + (Op.SET, Op.ACCESS, Op.ASM, Op.DECL, Op.MULTIDECL, Op.LABEL)

@dataclass
class Code:
    op:    Op
    dest:  Optional[str] = None
    args:  tuple = ()
    refs:  tuple = ()
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
    if isinstance(op, str):
        op = Op[op.upper()]
    assert op in INSTRUCTIONS

    if op in (Op.ADD, Op.SUB, Op.MUL, Op.GT, Op.LT, Op.GET):
        a, b = kwargs.pop('refs')
        dest = kwargs.pop('dest')
        assert not kwargs
        return Code(op, dest=dest, refs=(a, b))
    if op == Op.LIT:
        ty, idx, val, *_ = kwargs.pop('args'); assert not _
        dest = kwargs.pop('dest')
        assert not kwargs
        return Code(op, dest=dest, args=(ty, idx, int(val)))
    if op == Op.PRINT:
        refs = kwargs.pop('refs')
        assert not kwargs
        return Code(op, refs=refs)
    if op in (Op.REF, Op.MOVE, Op.ALLOC):
        a, *_ = kwargs.pop('refs'); assert not _
        dest = kwargs.pop('dest')
        assert not kwargs
        return Code(op, dest=dest, refs=(a,))
    if op == Op.BR:
        c_, *_ = kwargs.pop('refs'); assert not _
        l, r = kwargs.pop('args')
        assert not kwargs
        return Code(op, args=(l, r), refs=(c_, ))
    if op == Op.JMP:
        a, *_ = kwargs.pop('args'); assert not _
        assert not kwargs
        return Code(op, args=(a,))
    if op == Op.RET:
        refs = kwargs.pop('refs', tuple())
        assert not kwargs
        return Code(op, refs=refs)
    if op == Op.SET:
        obj, idx, val = kwargs.pop('refs')
        assert not kwargs
        return Code(op, refs=(obj, idx, val))

    assert False, f'{op}, {kwargs}'
