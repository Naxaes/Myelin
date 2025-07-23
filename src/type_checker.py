import sys

import errors
from ir import Op
from location import Location
from type import *


# -- TODO --
#   * Global type checking: https://www.youtube.com/watch?v=fDTt_uo0F-g&t=3343s&ab_channel=ChariotSolutions


class TypeChecker:
    def __init__(self, name, source, functions, data, constants, user_types):
        self.name = name
        self.source = source
        self.functions = functions
        self.data = data
        self.constants = constants
        self.env = {}
        self.registry = TypeRegistry()
        self.builtins = {
            None:       InferredType(),
            'void':     PrimitiveType(name='void', size=0),
            'bool':     PrimitiveType(name='bool', size=1),
            'char':     PrimitiveType(name='char', size=1),
            'int':      PrimitiveType(name='int',  size=8),
            'i8':       PrimitiveType(name='i8',   size=1),
            'i16':      PrimitiveType(name='i16',  size=2),
            'i32':      PrimitiveType(name='i32',  size=4),
            'i64':      PrimitiveType(name='i64',  size=8),
            'real':     PrimitiveType(name='real', size=8),
            'str':      PointerType(PrimitiveType(name='char',  size=1)),
            'ptr':      PointerType(PrimitiveType(name='void',  size=0)),
            'void*':    PointerType(PrimitiveType(name='void',  size=0)),
            'char*':    PointerType(PrimitiveType(name='char',  size=1)),
        }
        self.user_types = user_types
        self.types = []
        for n, t in self.user_types.items():
            self.user_types[n] = StructType(n, {
                x: self.builtins[y[0]] if y[0] in self.builtins else self.user_types[y[0]]  for x, y in t.items()
            })

    def lookup_type(self, name):
        if name in self.builtins:
            return self.builtins[name]
        elif name in self.user_types:
            return self.user_types[name]
        else:
            raise RuntimeError(f'Unknown type {name}')

    def type_of(self, block, arg):
        if type(arg) == str:
            if arg in self.env:
                return self.env[arg]
            else:
                value = self.constants[arg]
                if type(value) == int:
                    return self.builtins['int']
                else:
                    assert False, 'Not implemented'
        else:
            return self.env[block.instructions[arg].dest]

    def set_type(self, block, arg, t):
        if type(arg) == str:
            if arg in self.env:
                self.env[arg] = t
            else:
                self.constants[arg] = t
        else:
            self.env[block.instructions[arg].dest] = t

    @staticmethod
    def check(module) -> dict[str, dict[str, Type]]:
        functions = module.functions
        data = module.data
        constants = module.constants
        user_types = module.types
        self = TypeChecker(module.name, module.source, functions, data, constants, user_types)
        types = self.check_()
        for func_name, env in types.items():
            for name, t in env.items():
                if isinstance(t, InferredType):
                    func = module.functions[func_name]
                    for block in func.blocks:
                        for c in block.instructions:
                            if c.dest == name:
                                raise errors.error(module.name, module.source, c.token.begin, c.token.end, f"Type inference failed for {func_name} {name}. Type is still inferred.")
                    raise errors.error(self.name, self.source, Location(0, 1, 1), Location(0, 1, 1), f"Type inference failed for {func_name} {name}. Type is still inferred.")
        return types

    def check_(self) -> dict[str, dict[str, Type]]:
        """Local reasoning type checking"""
        self.types = {}
        for function in self.functions.values():
            self.env = { }
            code = list(function.code())
            for block, code in code + list(reversed(code)):
                if code.op == Op.LIT:
                    self.infer_lit(code)
                elif code.op in (Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD, Op.AND, Op.OR, Op.EQ, Op.NEQ, Op.LT):
                    a = self.type_of(block, code.lhs())
                    b = self.type_of(block, code.rhs())
                    t = a.operation(code.op, b)
                    self.env[code.dest] = t
                elif code.op == Op.ACCESS:
                    obj = self.type_of(block, code.obj())
                    attr = code.attr()
                    try:
                        self.env[code.dest] = obj.get_attribute(attr)
                    except AttributeError:
                        raise errors.error(self.name, self.source, code.token.begin, code.token.end, f"Cannot access attribute '{attr}' of {obj}.")
                elif code.op == Op.DECL:
                    if code.refs:
                        a = self.lookup_type(code.type())
                        b = self.type_of(block, code.expr())
                        if not b.is_subtype_of(a):
                            raise errors.error(self.name, self.source, code.token.begin, code.token.end, f'Type error between {a} and {b}')
                        if isinstance(a, InferredType):
                            self.env[code.dest] = b
                        else:
                            self.env[code.dest] = a
                    else:
                        assert False, "Not implemented"
                elif code.op == Op.MULTIDECL:
                    a = self.type_of(block, code.expr())
                    for i, n in enumerate(code.args):
                        self.env[n] = a[i]
                elif code.op == Op.ASSIGN:
                    a = self.type_of(block, code.target())
                    b = self.type_of(block, code.expr())
                    if not b.is_subtype_of(a):
                        raise errors.error(self.name, self.source, code.token.begin, code.token.end, f'Type error between {a} and {b}')
                elif code.op == Op.LABEL:
                    pass
                elif code.op == Op.CALL:
                    f = self.functions.get(code.args[0])
                    if f is None:
                        raise errors.error(self.name, self.source, code.token.begin, code.token.end, f"Function '{code.args[0]}' not found.")
                    args = code.refs[:]
                    if len(f.params) != len(args):
                        raise errors.error(self.name, self.source, code.token.begin, code.token.end, f'Passing wrong amount of arguments to {f.name}. Expected {len(f.params)}, but got {len(args)}')
                    for i, (name, t) in enumerate(f.params.items()):
                        a = self.lookup_type(t[0])
                        b = self.type_of(block, args[i])
                        if not b.is_subtype_of(a):
                            print(f'Error in {function.name} calling {f.name} at argument {i} ({name})', file=sys.stderr)
                            raise errors.error(self.name, self.source, code.token.begin, code.token.end, f'Type error between {a} and {b}')
                    if len(f.returns) == 0:
                        self.env[code.dest] = self.builtins[None]
                    elif len(f.returns) == 1:
                        ret = f.returns[0][1]
                        self.env[code.dest] = self.lookup_type(ret)
                    else:
                        self.env[code.dest] = tuple(self.lookup_type(f.returns[i][1]) for i in range(len(f.returns)))
                elif code.op == Op._:
                    f = code.args[0]
                    ret = f.returns[code.args[1]][1]
                    self.env[code.dest] = self.lookup_type(ret)
                elif code.op == Op.PARAM:
                    self.env[code.dest] = self.lookup_type(code.type())
                elif code.op == Op.FIELD:
                    self.env[code.dest] = self.type_of(block, *code.refs)
                elif code.op == Op.INIT:
                    thing = self.lookup_type(code.type())
                    assert len(thing.fields) == len(code.refs)
                    for (n, t), arg in zip(thing.fields.items(), code.refs):
                        a = t
                        b = self.type_of(block, arg)
                        if not b.is_subtype_of(a):
                            raise errors.error(self.name, self.source, code.token.begin, code.token.end, f'Type error between {a} and {b}')
                    self.env[code.dest] = thing
                elif code.op == Op.SYSCALL:
                    self.env[code.dest] = self.builtins[None] if code.dest not in self.env else self.env[code.dest]
                elif code.op == Op.ASM:
                    self.env[code.dest] = self.type_of(block, *code.refs)
                elif code.op == Op.INDEX:
                    target = self.type_of(block, code.target())
                    if target.name == 'str' or target.name == 'char*':
                        self.env[code.dest] = self.builtins['char']
                    else:
                        assert isinstance(target, PointerType), f"Cannot index a '{target}'"
                        self.env[code.dest] = target.pointee
                elif code.op == Op.REF:
                    target = self.type_of(block, code.target())
                    self.env[code.dest] = PointerType(target)
                elif code.op == Op.MOVE:
                    target = self.type_of(block, code.target())
                    self.env[code.dest] = target
                elif code.op == Op.BRW:
                    target = self.type_of(block, code.target())
                    self.env[code.dest] = target
                elif code.op == Op.COPY:
                    target = self.type_of(block, code.target())
                    self.env[code.dest] = target
                elif code.op == Op.AS:
                    target = code.target()
                    obj = self.type_of(block, target)
                    to  = self.lookup_type(code.type())
                    if not obj.is_subtype_of(to):
                        raise errors.error(self.name, self.source, code.token.begin, code.token.end, f'Type error between {obj} and {to}')
                    dest = target if isinstance(target, str) else block.instructions[target].dest
                    self.env[dest] = to
                    self.env[code.dest] = to
                elif code.op == Op.BR:
                    pass
                elif code.op == Op.JMP:
                    pass
                elif code.op == Op.RET:
                    if function.is_module:
                        continue
                    elif len(function.returns) != len(code.refs):
                        if ((len(function.returns) == 1 and function.returns[0][1] == 'void') or (len(function.returns) == 0)) and len(code.refs) == 0:
                            self.env[code.dest] = self.builtins['void']
                        else:
                            raise errors.error(self.name, self.source, code.token.begin, code.token.end, f"Returning wrong amount of returns to '{function.name}'. Expected {len(function.returns)}, but got {len(code.refs)}")
                    elif len(function.returns) == 0 and len(code.refs) == 0:
                        self.env[code.dest] = self.builtins['void']

                    for ret, arg in zip(function.returns, code.refs):
                        a = self.lookup_type(ret[1])
                        b = self.type_of(block, arg)
                        if not b.is_subtype_of(a):
                            raise errors.error(self.name, self.source, code.token.begin, code.token.end, f'Type error between {a} and {b}')
                        self.set_type(block, arg, a)
                else:
                    assert False, f'Unknown instruction {code}'
            self.types[function.name] = self.env
        return self.types

    def infer_lit(self, code):
        assert code.op == Op.LIT
        assert code.type() is not None, "All literals have a type"
        assert len(code.args) == 3, "Expected type, index and data"

        t, index, data = code.args
        match t:
            case 'str':
                ty = ArrayType(self.builtins['char'], len(data.replace('\\', '')))
                self.env[code.dest] = ty
            case 'int':
                self.env[code.dest] = LiteralType(int(data))
            case 'real':
                self.env[code.dest] = self.lookup_type(t)
            case _:
                raise TypeError(f'Unknown type {code}')



