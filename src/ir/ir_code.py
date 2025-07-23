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
    DOT = auto()        # Prefix dot (.x)
    ACCESS = auto()     # Infix dot (x.y)
    AS = auto()
    INDEX = auto()
    ASSIGN = auto()
    LIT = auto()
    BRW = auto()
    REF = auto()
    MOVE = auto()
    COPY = auto()
    PARAM = auto()
    FIELD = auto()
    INIT = auto()
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
    Op.DOT, Op.AS, Op.INDEX, Op.ASSIGN, Op.LIT, Op.REF, Op.MOVE, Op.COPY, Op.BRW, Op.PARAM, Op.FIELD, Op.INIT
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
    def expr(self): return self.refs[0]
    def obj(self): return self.refs[0]
    def attr(self): return self.refs[1]
    def target(self): return self.refs[0]
    def type(self): return self.args[0] if self.args else None

    def to_text(self) -> str:
        match self.op:
            case Op.NOP:
                return f'nop'
            case Op.ADD:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.SUB:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.MUL:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.DIV:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.MOD:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.AND:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.OR:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.NOT:
                return f'not %{self.refs[0]}'
            case Op.EQ:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.NEQ:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.GT:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.LT:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.GTE:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.LTE:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.DOT:
                return f'{self.dest} := %{self.refs[0]} {self.token.kind} %{self.refs[1]}'
            case Op.AS:
                return f'{self.dest} := %{self.refs[0]} as {self.args[0]}'
            case Op.INDEX:
                return f'{self.dest} := %{self.refs[0]}[%{self.refs[1]}]'
            case Op.ASSIGN:
                return f'%{self.refs[0]} = %{self.refs[1]}'
            case Op.LIT:
                return f'{self.dest} : {self.args[0]} = {self.args[2]}'
            case Op.BRW:
                return f'brw %{self.refs[0]}'
            case Op.REF:
                return f'ref %{self.refs[0]}'
            case Op.MOVE:
                return f'move %{self.refs[0]}'
            case Op.COPY:
                return f'copy %{self.refs[0]}'
            case Op.PARAM:
                return f'{self.dest}: {self.args[0]}'
            case Op.FIELD:
                return f'{self.dest} :: .{self.args[1]} = %{self.refs[0]}'
            case Op.INIT:
                return f'{self.dest} := {self.args[0]}{{{", ".join(f"%{i}" for i in self.refs)}}}'
            case Op.ACCESS:
                return f'{self.dest} := %{self.refs[0]}.%{self.refs[1]}'
            case Op.RET:
                return f'ret {", ".join(f"%{i}" for i in self.refs)}'
            case Op.PRINT:
                return f'print %{self.refs[0]}'
            case Op.CALL:
                return f'{self.dest} = {self.args[0]}({", ".join(f"%{i}" for i in self.refs)})'
            case Op.ALLOC:
                return f'alloc %{self.refs[0]}'
            case Op.FREE:
                return f'free %{self.refs[0]}'
            case Op.SYSCALL:
                return f'syscall %{self.refs[0]}'
            case Op.DECL:
                return f'{self.dest} := %{self.refs[0]}'
            case Op.MULTIDECL:
                return f'{", ".join(str(i) for i in self.args)} := {", ".join(f"%{i}" for i in self.refs)}'
            case Op.ASM:
                return f'asm %{self.refs[0]}'
            case Op.BR:
                return f'if %{self.refs[0]} then ${self.args[0]} else ${self.args[1]}'
            case Op.JMP:
                return f'jmp ${self.args[0]}'
            case Op.SET:
                return f'set %{self.refs[0]}'
            case Op._:
                return f'_ %{self.refs[0]}'
            case Op.LABEL:
                return f'label %{self.refs[0]}'
            case _:
                raise Exception(f'Unknown op: {self.op}')


def c(**kwargs):
    op = kwargs.pop('op')
    if isinstance(op, str):
        op = Op[op.upper()]
    assert op in INSTRUCTIONS

    if op in (Op.ADD, Op.SUB, Op.MUL, Op.GT, Op.LT):
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
