from type import *


class TypeResolver:
    def __init__(self, builtins, user_types):
        self.builtins = builtins
        self.user_types = user_types

    def resolve(self, name):
        if name in self.builtins:
            return self.builtins[name]
        elif name in self.user_types:
            return self.user_types[name]
        else:
            raise TypeError(f"Unknown type '{name}'")


class CoercionPolicy:
    def __init__(self):
        pass

    def can_coerce(self, from_type: Type, to_type: Type) -> bool:
        return from_type.can_coerce_to(to_type)

    def common_supertype(self, a: Type, b: Type) -> Type:
        if a.name == 'inferred':  return b
        if b.name == 'inferred':  return a
        if self.can_coerce(b, a): return a
        if self.can_coerce(a, b): return b
        raise TypeError(f"Incompatible types: {a}, {b}")


class TypeChecker:
    def __init__(self, module):
        self.functions = module.functions
        self.constants = module.constants
        self.data = module.data
        self.user_types = module.types
        self.builtins = self.build_builtin_types()
        self.resolver = TypeResolver(self.builtins, self.user_types)
        self.policy = CoercionPolicy()
        self.registry = TypeRegistry()
        self.types = {}
        self.mapping = {}

        self.initialize_user_types()

    def build_builtin_types(self):
        return {
            None:       PrimitiveType('inferred', 0),
            'byte':     PrimitiveType('byte', 1),
            'int':      PrimitiveType('int', 8),
            'real':     PrimitiveType('real', 8),
            'bool':     PrimitiveType('bool', 1),
            'str':      PointerType(PrimitiveType('byte', 1)),
            'ptr':      PointerType(PrimitiveType('void', 8)),
            'void*':    PointerType(PrimitiveType('void', 8)),
            'byte*':    PointerType(PrimitiveType('byte', 1)),
        }

    def initialize_user_types(self):
        for name, definition in self.user_types.items():
            if isinstance(definition, dict):
                fields = {k: self.resolver.resolve(v[0]) for k, v in definition.items() if k != '__name__'}
                self.user_types[name] = StructType(name, fields)

    def get_arg(self, block, arg):
        if isinstance(arg, str):
            if arg in self.mapping:
                return self.mapping[arg]
            val = self.constants[arg]
            if isinstance(val, int):
                return self.builtins['int']
            raise NotImplementedError(f"Unknown literal type for constant {arg}")
        return self.mapping[block.instructions[arg].dest]

    def type_check(self):
        for name, function in self.functions.items():
            self.mapping = {}
            for block in function.blocks:
                for instr in block.instructions:
                    self.process_instruction(instr, block)
                self.check_terminator(block.terminator, function)
            self.types[function.name] = self.mapping
        return self.types

    def process_instruction(self, instr, block):
        method = getattr(self, f"visit_{instr.op}", None)
        if not method:
            raise RuntimeError(f"Unknown instruction {instr.op}")
        method(instr, block)

    def check_terminator(self, term, function):
        if term.op == 'ret':
            if function.is_module:
                return
            if len(term.refs) != len(function.returns):
                raise TypeError(f"Function '{function.name}' returns wrong number of values")
            for ref, (name, tname) in zip(term.refs, function.returns):
                expected = self.resolver.resolve(tname)
                actual = self.get_arg(term.block, ref)
                self.policy.common_supertype(expected, actual)

    def visit_lit(self, instr, _):
        tname = instr.type
        index, data = instr.args
        if tname == 'str':
            ty = ArrayType(self.builtins['byte'], len(data.replace('\\', '')))
            ty = self.registry.intern(ty)
        else:
            ty = self.builtins[tname]
        self.mapping[instr.dest] = ty

    def visit_add(self, instr, block):
        a = self.get_arg(block, instr.refs[0])
        b = self.get_arg(block, instr.refs[1])
        t = self.policy.common_supertype(a, b)
        self.mapping[instr.dest] = t

    def visit_assign(self, instr, block):
        a = self.get_arg(block, instr.refs[0])
        b = self.get_arg(block, instr.refs[1])
        self.policy.common_supertype(a, b)

    # Define other visit_* methods here for: call, decl, param, field, dot, init, &, as, etc.

