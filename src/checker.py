from type import *


# -- TODO --
#   * Global type checking: https://www.youtube.com/watch?v=fDTt_uo0F-g&t=3343s&ab_channel=ChariotSolutions


class Checker:
    def __init__(self, functions, data, constants, user_types):
        self.functions = functions
        self.data = data
        self.constants = constants
        self.mapping = {}
        self.builtins = {
            None:       PrimitiveType(name='inferred', size=0),
            'byte':     PrimitiveType(name='byte',  size=1),
            'int':      PrimitiveType(name='int',  size=8),
            'real':     PrimitiveType(name='real', size=8),
            'bool':     PrimitiveType(name='bool', size=1),
            'str':      PointerType(PrimitiveType(name='byte',  size=1)),
            'ptr':      PointerType(PrimitiveType('void', 8)),
            'void*':    PointerType(PrimitiveType('void', 8)),
            'byte*':    PointerType(PrimitiveType(name='byte',  size=1)),
        }
        self.user_types = user_types
        self.types = []
        self.registry = TypeRegistry()
        for n, t in self.user_types.items():
            if type(t) == dict:
                self.user_types[n] = StructType(n, {x: self.builtins[y[0]] for x, y in t.items() if x != '__name__'})


    def get_arg(self, block, arg):
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

    def type_check(self, a, b):
        if a.name == 'inferred' and b.name == 'inferred':
            raise RuntimeError(f'No types for {a} and {b}')
        if a.name == 'inferred':
            return b
        if b.name == 'inferred':
            return a
        if b.is_subtype_of(a):
            return a

        # TODO: Remove these hacks.
        if ((a.name == 'void*' and b.name == 'str')
                or (b.name == 'void*' and a.name == 'str')
                or (a.name == 'void*' and b.name == 'byte*')
                or (a.name == 'byte*' and b.name.startswith('byte['))
                or (a.name == 'byte' and b.name == 'int')
        ):
            return b
        if isinstance(a, PointerType) and b.name == 'int':
            return a
        raise RuntimeError(f'Type error between {a} and {b}')

    @staticmethod
    def check(module):
        functions = module.functions
        data = module.data
        constants = module.constants
        user_types = module.types
        self = Checker(functions, data, constants, user_types)
        return self.check_()

    def check_(self):
        """Local reasoning type checking"""
        self.types = {}
        for name, function in self.functions.items():
            self.mapping = { }
            for block in function.blocks:
                for code in block.instructions:
                    if code.op == 'lit':
                        self.infer_lit(code)
                    elif code.op in ('+', '-', '*', '/', '%', '==', '!=', '<'):
                        a = self.get_arg(block, code.refs[0])
                        b = self.get_arg(block, code.refs[1])
                        t = self.type_check(a, b)
                        self.mapping[code.dest] = self.builtins['bool' if code.op in ('==', '!=', '<') else t.name]
                    elif code.op in ('and', 'or'):
                        a = self.get_arg(block, code.refs[0])
                        b = self.get_arg(block, code.refs[1])
                        self.type_check(a, b)
                        self.mapping[code.dest] = self.builtins['bool']
                    elif code.op == '.':
                        obj = self.get_arg(block, code.refs[0])
                        attr = code.refs[1]
                        self.mapping[code.dest] = obj.get_attribute(attr)
                    elif code.op == 'decl':
                        if code.refs:
                            a = self.get_arg(block, code.refs[0])
                            t = self.builtins[code.type]
                            self.mapping[code.dest] = self.type_check(a, t)
                        else:
                            assert False, "Not implemented"
                    elif code.op == 'multidecl':
                        a = self.get_arg(block, code.refs[0])
                        for i, n in enumerate(code.args):
                            self.mapping[n] = a[i]
                    elif code.op == 'assign':
                        a = self.get_arg(block, code.refs[0])
                        b = self.get_arg(block, code.refs[1])
                        self.type_check(a, b)
                    elif code.op == 'label':
                        pass
                    elif code.op == 'call':
                        f = self.functions[code.args[0]]
                        args = code.refs[:]
                        if len(f.params) != len(args):
                            raise RuntimeError(f'Passing wrong amount of arguments to {f.name}. Expected {len(f.params)}, but got {len(args)}')
                        for i, (name, t) in enumerate(f.params.items()):
                            a = self.get_arg(block, args[i])
                            self.type_check(self.builtins.get(t[0]) or self.user_types[t[0]], a)
                        if len(f.returns) == 0:
                            self.mapping[code.dest] = self.builtins[None]
                        elif len(f.returns) == 1:
                            self.mapping[code.dest] = self.builtins[f.returns[0][1]]
                        else:
                            self.mapping[code.dest] = tuple(self.builtins[f.returns[i][1]] for i in range(len(f.returns)))
                    elif code.op == '_':
                        f = code.args[0]
                        self.mapping[code.dest] = self.builtins[f.returns[code.args[1]][1]]
                    elif code.op == 'param':
                        self.mapping[code.dest] = self.builtins.get(code.type) or self.user_types[code.type]
                    elif code.op == 'field':
                        self.mapping[code.dest] = self.builtins[code.type]
                    elif code.op == 'init':
                        thing = self.builtins.get(code.type) or self.user_types[code.type]
                        assert len(thing.fields) == len(code.refs)
                        for (n, t), arg in zip(thing.fields.items(), code.refs):
                            actual = self.get_arg(block, arg)
                            expect = t
                            self.type_check(expect, actual)
                        self.mapping[code.dest] = thing
                    elif code.op == 'syscall':
                        self.mapping[code.dest] = self.builtins[None]
                    elif code.op == 'index':
                        target = self.get_arg(block, code.refs[0])
                        if target.name == 'str' or target.name == 'byte*':
                            self.mapping[code.dest] = self.builtins['byte']
                        else:
                            assert isinstance(target, PointerType), f"Cannot index a '{target}'"
                            self.mapping[code.dest] = target.pointee
                    elif code.op == '&':
                        target = self.get_arg(block, code.refs[0])
                        self.mapping[code.dest] = PointerType(target)
                    elif code.op == 'as':
                        obj = self.get_arg(block, code.refs[0])
                        to  = self.builtins[code.type]
                        assert obj.can_coerce_to(to)
                        self.mapping[block.instructions[code.refs[0]].dest] = to
                        self.mapping[code.dest] = to
                        code.dest = block.instructions[code.refs[0]].dest
                    else:
                        assert False, f'Unknown instruction {code}'

                code = block.terminator
                if code.op == 'br':
                    pass
                elif code.op == 'jmp':
                    pass
                elif code.op == 'leave':
                    pass
                elif code.op == 'ret':
                    if function.is_module:
                        continue
                    if len(function.returns) != len(code.refs):
                        raise RuntimeError(f'Returning wrong amount of returns to {function.name}. Expected {len(function.returns)}, but got {len(code.refs)}')
                    for ret, arg in zip(function.returns, code.refs):
                        arg = self.get_arg(block, arg)
                        self.type_check(self.builtins[ret[1]], arg)
                else:
                    assert False, f"Unknown terminator {code}"
            self.types[function.name] = self.mapping
        return self.types

    def infer_lit(self, code):
        assert code.op == 'lit'
        assert code.type is not None, "All literals have a type"
        assert len(code.args) == 2, "Expected index and data"

        index, data = code.args
        match code.type:
            case 'str':
                ty = ArrayType(self.builtins['byte'], len(data))
                ty = self.registry.intern(ty)
                self.mapping[code.dest] = ty
            case 'int':
                self.mapping[code.dest] = self.builtins[code.type]
            case 'real':
                self.mapping[code.dest] = self.builtins[code.type]
            case _:
                raise TypeError(f'Unknown type {code}')



