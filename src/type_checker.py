from ir import Op
from type import *


# -- TODO --
#   * Global type checking: https://www.youtube.com/watch?v=fDTt_uo0F-g&t=3343s&ab_channel=ChariotSolutions


class TypeChecker:
    def __init__(self, functions, data, constants, user_types):
        self.functions = functions
        self.data = data
        self.constants = constants
        self.mapping = {}
        self.registry = TypeRegistry()
        self.builtins = {
            None:       InferredType(),
            'bool':     PrimitiveType(name='bool', size=1),
            'char':     PrimitiveType(name='char', size=1),
            'int':      PrimitiveType(name='int',  size=8),
            'real':     PrimitiveType(name='real', size=8),
            'str':      PointerType(PrimitiveType(name='char',  size=1)),
            'ptr':      PointerType(PrimitiveType('void', 0)),
            'void*':    PointerType(PrimitiveType('void', 0)),
            'char*':    PointerType(PrimitiveType(name='char',  size=1)),
        }
        self.user_types = user_types
        self.types = []
        for n, t in self.user_types.items():
            if '__name__' in t:
                self.user_types[n] = StructType(n, {x: self.builtins[y[0]] for x, y in t.items() if x != '__name__'})
            else:
                assert False, f'Unknown thing {t} for {n}'

    def lookup_type(self, name):
        if name in self.builtins:
            return self.builtins[name]
        elif name in self.user_types:
            return self.user_types[name]
        else:
            raise RuntimeError(f'Unknown type {name}')

    def type_of(self, block, arg):
        if type(arg) == str:
            if arg in self.mapping:
                return self.mapping[arg]
            else:
                value = self.constants[arg]
                if type(value) == int:
                    return self.builtins['int']
                else:
                    assert False, 'Not implemented'
        else:
            return self.mapping[block.instructions[arg].dest]

    @staticmethod
    def check(module) -> dict[str, dict[str, Type]]:
        functions = module.functions
        data = module.data
        constants = module.constants
        user_types = module.types
        self = TypeChecker(functions, data, constants, user_types)
        return self.check_()

    def check_(self) -> dict[str, dict[str, Type]]:
        """Local reasoning type checking"""
        code = None
        self.types = {}
        for function in self.functions.values():
            self.mapping = { }
            for block, code in function.code():
                if code.op == Op.LIT:
                    self.infer_lit(code)
                elif code.op in (Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD, Op.AND, Op.OR, Op.EQ, Op.NEQ, Op.LT):
                    a = self.type_of(block, code.lhs())
                    b = self.type_of(block, code.rhs())
                    t = a.operation(code.op, b)
                    self.mapping[code.dest] = t
                elif code.op == Op.ACCESS:
                    obj = self.type_of(block, code.obj())
                    attr = code.attr()
                    self.mapping[code.dest] = obj.get_attribute(attr)
                elif code.op == Op.DECL:
                    if code.refs:
                        a = self.lookup_type(code.type())
                        b = self.type_of(block, code.expr())
                        if not b.is_subtype_of(a): raise RuntimeError(f'Type error between {a} and {b}')
                        self.mapping[code.dest] = b
                    else:
                        assert False, "Not implemented"
                elif code.op == Op.MULTIDECL:
                    a = self.type_of(block, code.expr())
                    for i, n in enumerate(code.args):
                        self.mapping[n] = a[i]
                elif code.op == Op.ASSIGN:
                    a = self.type_of(block, code.target())
                    b = self.type_of(block, code.expr())
                    if not b.is_subtype_of(a): raise RuntimeError(f'Type error between {a} and {b}')
                elif code.op == Op.LABEL:
                    pass
                elif code.op == Op.CALL:
                    f = self.functions[code.args[0]]
                    args = code.refs[:]
                    if len(f.params) != len(args):
                        raise RuntimeError(f'Passing wrong amount of arguments to {f.name}. Expected {len(f.params)}, but got {len(args)}')
                    for i, (name, t) in enumerate(f.params.items()):
                        a = self.lookup_type(t[0])
                        b = self.type_of(block, args[i])
                        if not b.is_subtype_of(a): raise RuntimeError(f'Type error between {a} and {b}')
                    if len(f.returns) == 0:
                        self.mapping[code.dest] = self.builtins[None]
                    elif len(f.returns) == 1:
                        ret = f.returns[0][1]
                        self.mapping[code.dest] = self.lookup_type(ret)
                    else:
                        self.mapping[code.dest] = tuple(self.lookup_type(f.returns[i][1]) for i in range(len(f.returns)))
                elif code.op == Op._:
                    f = code.args[0]
                    ret = f.returns[code.args[1]][1]
                    self.mapping[code.dest] = self.lookup_type(ret)
                elif code.op == Op.PARAM:
                    self.mapping[code.dest] = self.lookup_type(code.type())
                elif code.op == Op.FIELD:
                    self.mapping[code.dest] = self.lookup_type(code.type())
                elif code.op == Op.INIT:
                    thing = self.lookup_type(code.type())
                    assert len(thing.fields) == len(code.refs)
                    for (n, t), arg in zip(thing.fields.items(), code.refs):
                        a = t
                        b = self.type_of(block, arg)
                        if not b.is_subtype_of(a): raise RuntimeError(f'Type error between {a} and {b}')
                    self.mapping[code.dest] = thing
                elif code.op == Op.SYSCALL:
                    self.mapping[code.dest] = self.builtins[None]
                elif code.op == Op.ASM:
                    self.mapping[code.dest] = self.builtins[None]
                elif code.op == Op.INDEX:
                    target = self.type_of(block, code.target())
                    if target.name == 'str' or target.name == 'char*':
                        self.mapping[code.dest] = self.builtins['char']
                    else:
                        assert isinstance(target, PointerType), f"Cannot index a '{target}'"
                        self.mapping[code.dest] = target.pointee
                elif code.op == Op.REF:
                    target = self.type_of(block, code.target())
                    self.mapping[code.dest] = PointerType(target)
                elif code.op == Op.MOVE:
                    target = self.type_of(block, code.target())
                    self.mapping[code.dest] = target
                elif code.op == Op.BRW:
                    target = self.type_of(block, code.target())
                    self.mapping[code.dest] = target
                elif code.op == Op.COPY:
                    target = self.type_of(block, code.target())
                    self.mapping[code.dest] = target
                elif code.op == Op.AS:
                    target = code.target()
                    obj = self.type_of(block, target)
                    to  = self.lookup_type(code.type())
                    if not obj.is_subtype_of(to): raise RuntimeError(f'Type error between {obj} and {to}')
                    dest = target if isinstance(target, str) else block.instructions[target].dest
                    self.mapping[dest] = to
                    self.mapping[code.dest] = to
                elif code.op == Op.BR:
                    pass
                elif code.op == Op.JMP:
                    pass
                elif code.op == Op.RET:
                    if function.is_module:
                        continue
                    if len(function.returns) != len(code.refs):
                        raise RuntimeError(f"Returning wrong amount of returns to '{function.name}'. Expected {len(function.returns)}, but got {len(code.refs)}")
                    for ret, arg in zip(function.returns, code.refs):
                        a = self.lookup_type(ret[1])
                        b = self.type_of(block, arg)
                        if not b.is_subtype_of(a): raise RuntimeError(f'Type error between {a} and {b}')
                else:
                    assert False, f'Unknown instruction {code}'
            self.types[function.name] = self.mapping
        return self.types

    def infer_lit(self, code):
        assert code.op == Op.LIT
        assert code.type() is not None, "All literals have a type"
        assert len(code.args) == 3, "Expected type, index and data"

        t, index, data = code.args
        match t:
            case 'str':
                ty = ArrayType(self.builtins['char'], len(data.replace('\\', '')))
                self.mapping[code.dest] = ty
            case 'int':
                self.mapping[code.dest] = self.lookup_type(t)
            case 'real':
                self.mapping[code.dest] = self.lookup_type(t)
            case _:
                raise TypeError(f'Unknown type {code}')



