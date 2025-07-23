from ir import Op
from type import LiteralType, Type, StructType


def register_to_size(src, size):
    if size == 1:
        if src in ('rsi', 'rsp', 'rbp', 'rdi'):
            return src[1:] + 'l'
        return src[1] + 'l' if not src[1].isnumeric() else src + 'b'
    elif size == 2:
        return src[1] + 'x' if not src[1].isnumeric() else src + 'w'
    elif size == 4:
        return 'e' + src[1] + 'x' if not src[1].isnumeric() else src + 'd'
    elif size == 8:
        return src
    assert False


class X86_64_Generator:
    def __init__(self, functions, data, constants, types):
        # https://devblogs.microsoft.com/oldnewthing/20231204-00/?p=109095
        # Nested function - Static chain pointer

        # https://uops.info/
        self.functions = functions
        self.mapping = {}
        self.vars = {}
        self.data = data
        self.types = types
        self.constants = constants
        self.save = ['rbx', 'r12', 'r13', 'r14', 'r15']
        self.scratch = ['rax', 'rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9', 'r10', 'r11']
        self.regs = self.scratch + self.save

        self.code = ''
        self.stack_size = 0

    def type_of(self, function, code) -> Type:
        return self.types[function.name][code.dest]

    @staticmethod
    def generate(module, types):
        functions = module.functions
        data = module.data
        constants = module.constants

        self = X86_64_Generator(functions, data, constants, types)
        for function in self.functions.values():
            if len(function.blocks) == 0:
                continue
            self.code += f"; -------- '{function.name}' --------\n{function.name}:\n"
            self.mapping = { }
            self.vars    = { }
            for block_offset, block in enumerate(function.blocks):
                self.mapping = self.vars.copy()
                self.code += f'.{block.label}:\n'
                for code in block.instructions:
                    if code.op == Op.LIT:
                        self.generate_lit(function, block, code)
                    elif code.op in (Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD, Op.EQ, Op.NEQ, Op.LT, Op.AND, Op.OR):
                        self.generate_bin(function, block, code)
                    elif code.op == Op.DECL:
                        self.generate_decl(function, block, code)
                    elif code.op == Op.MULTIDECL:
                        self.generate_multidecl(function, block, code)
                    elif code.op == Op.ASSIGN:
                        self.generate_assign(function, block, code)
                    elif code.op == Op.LABEL:
                        self.code += f'.{code.args[0]}:\n'
                    elif code.op == Op.CALL:
                        self.generate_call(function, block, code)
                    elif code.op == Op.PARAM:
                        self.generate_param(code)
                    elif code.op == Op._:
                        # Pseudo-target
                        pass
                    elif code.op == Op.FIELD:
                        self.generate_field(function, block, code)
                    elif code.op == Op.INIT:
                        self.generate_init(function, block, code)
                    elif code.op == Op.SYSCALL:
                        self.generate_syscall(function, block, code)
                    elif code.op == Op.ASM:
                        self.generate_asm(function, block, code)
                    elif code.op == Op.INDEX:
                        self.generate_index(function, block, code)
                    elif code.op == Op.REF:
                        self.generate_dereference(function, block, code)
                    elif code.op == Op.AS:
                        target = code.refs[0]
                        src = target if isinstance(target, str) else block.instructions[target].dest
                        self.mapping[code.dest] = self.peek_reg(src)
                    elif code.op == Op.ACCESS:
                        self.generate_get(function, block, code)
                    else:
                        assert False, f'Unknown instruction {code}'

                code = block.terminator
                if code.op == Op.BR:
                    self.generate_ite(function, block, code)
                elif code.op == Op.JMP:
                    self.generate_jmp(function, code, block_offset)
                elif code.op == Op.RET:
                    self.generate_ret(function, block, code)
                else:
                    assert False, f"Unknown terminator {code}"

        data = ""
        for i, d in self.data.items():
            if type(d) == str:
                # data += f'string_{i}: db `{d}`, 0\n'
                # data += f'data_{i}: dq {len(d)}, string_{i}\n'
                data += f'data_{i}: db `{d}`, 0\n'

        return self.code, data

    def generate_init(self, function, block, code):
        ty = self.type_of(function, code)
        assert isinstance(ty, StructType), f'Invalid type {ty} to init'
        self.code += f'\t; {ty.name} {ty.fields}\n'
        self.code += f'\tsub rsp, {ty.size}\n'
        self.stack_size += ty.size
        names = []
        for i, ref in enumerate(code.refs, start=1):
            name = ref if type(ref) == str else block.instructions[ref].dest
            src = self.consume_reg(name)
            self.code += f'\tmov [rsp + {ty.size - 8 * i}], {src}\t\t; .{i-1} = {name}\n'
            names.append(name)
        dst = self.set_reg(code.dest)
        self.code += f'\tmov {dst}, rsp\t\t\t; {code.dest} : {ty.name} = {{ {", ".join(n for n in names)} }}\n\n'

    def add_code(self, *args, comment=None):
        if len(args) == 3:
            a = args[1] + ',' if len(args[1]) == 3 else args[1] + ', '
            self.code += f'\t{args[0]:<5} {a:<3} {args[2]:<3}'
        elif len(args) == 2:
            self.code += f'\t{args[0]:<5} {args[1]:<7}'
        elif len(args) == 1:
            self.code += f'\t{args[0]:<13}'
        else:
            assert False
        if comment: self.code += f'\t\t; {comment}'
        self.code += '\n'

    def generate_jmp(self, function, code, offset):
        if code.args[0] != offset + 1:  # No need to jump to next block.
            block = function.blocks[code.args[0]]
            self.add_code('jmp', f'.{block.label}')
            self.code += '\n'

    def generate_param(self, code):
        param = code.dest
        dst = self.set_reg(param)
        self.code += f'\t; {dst} := {param}\n\n'
        self.vars[code.dest] = dst

    def generate_call(self, function, block, code):
        func = self.functions[code.args[0]]
        pushed = self.prepare_function_call(function, block, code)
        self.add_code('call', func.name)
        self.finish_function_call(code, pushed, len(func.returns))

    def generate_syscall(self, function, block, code):
        pushed = self.prepare_function_call(function, block, code)
        self.add_code('syscall')
        self.finish_function_call(code, pushed, returns = 1)

    def generate_asm(self, function, block, code):
        ty, idx, val = block.instructions[code.refs[0]].args
        assert ty == 'str', f'Expected asm to be a string, got {ty}'
        code = '\n\t; Inline asm\n\t' + '\n\t'.join(val.split('\\n'))
        self.code += code + '\n'

    def finish_function_call(self, code, pushed, returns = 0):
        # FIXME: I need to write an actual register allocation algorithm...
        #        This is starting to get a bit too hacky.
        iterator = reversed(range(returns)) if self.vars else range(returns)
        for i in iterator:
            dest = code.dest if returns == 1 else f'{code.dest}.{i}'
            dst = self.set_reg(dest)
            if dst != self.regs[i]:
                self.add_code('mov', dst, self.regs[i], comment=f'ret {i} := {dest}')
            else:
                self.code += f'\t; {dst} = {dest}\n'
        for var, reg in reversed(pushed):
            self.add_code('pop', reg, comment=f'Restore {var}')
        self.code += '\n'

    def prepare_function_call(self, function, block, code):
        assert code.op == Op.CALL or code.op == Op.SYSCALL

        pushed = []
        for i, r in enumerate(self.regs):
            if pair := next(((name, reg) for name, reg in self.mapping.items() if reg == r), None):
                self.add_code('push', r, comment=f'Save {pair[0]}')
                pushed.append(pair)

        args = [(i, self.peek_reg(arg)) for i, arg in enumerate([
            arg if type(arg) == str else block.instructions[arg].dest
            for arg in code.refs
        ])]

        deferred = []
        temporaries = []
        while True:
            changed = False
            while args:
                i, src = args.pop(0)
                dst = self.regs[i]
                if dst in (x[1] for x in args) or dst in (x[1] for x in deferred):
                    deferred.append((i, src))
                    continue
                elif src != dst:
                    self.add_code('mov', dst, src)
                changed = True
            if not deferred:
                break
            if not changed:
                j = len(temporaries)
                v = self.regs[len(code.refs) + j + 1]
                b = deferred.pop(0)
                temporaries.append((v, b[0]))
                self.add_code('mov', v, b[1])
            args = deferred.copy()
            deferred = []
        for temp in temporaries:
            a, b = temp
            self.add_code('mov', self.regs[b], a)
        return pushed

    def generate_ret(self, function, block, code):
        for i, arg in enumerate(code.refs):
            var = arg if type(arg) == str else block.instructions[arg].dest
            src = self.mapping[var]
            if self.regs[i] != src:
                self.add_code('mov', self.regs[i], src)

        if function.is_main:
            self.code += '\t; End of module (implicit exit)\n'
            if self.mapping: self.add_code('mov', 'rdi', list(self.mapping.values())[-1])
            else: self.add_code('mov', 'rdi', '0')
            self.add_code('mov', 'rax', '0x2000000+1')
            self.add_code('syscall')
            self.code += '\n'
        elif function.is_module:
            pass
        else:
            # self.add_code('add', 'rsp', f'{self.stack_size}')
            self.stack_size = 0
            self.add_code('ret')
            self.code += '\n'

    def generate_ite(self, function, block, code):
        cond = block.instructions[code.refs[0]].dest
        left = function.blocks[code.args[0]]
        right = function.blocks[code.args[1]]
        src = self.consume_reg(cond)
        self.code += f'\t; if {cond} goto {left.label} else {right.label}\n'
        self.add_code('test', src, src)
        self.add_code('je', f'.{right.label}')
        self.code += '\n'

    def generate_decl(self, function, block, code):
        if self.type_of(function, code).name == 'func':
            return

        name = code.refs[0]
        name = name if type(name) == str else block.instructions[name].dest
        ty = self.type_of(function, code)
        if ty.size <= 8 or True:
            src = self.consume_reg(name)
            dst = self.set_reg(code.dest)
            self.code += f'\t; {code.dest} ({dst}) : {ty} = {name}\n\n'
            if dst != src:
                self.add_code('mov', dst, src)
            self.vars[code.dest] = dst
        else:
            assert False

    def generate_multidecl(self, function, block, code):
        for i, arg in enumerate(code.args):
            name = code.refs[0]
            name = name if type(name) == str else block.instructions[name].dest
            dest = f'{name}.{i}'
            ty = self.types[function.name][name][i]
            src = self.consume_reg(dest)
            dst = self.set_reg(arg)
            self.code += f'\t; {arg} ({dst}) : {ty} = {dest}\n\n'
            if dst != src:
                self.add_code('mov', dst, src)
            self.vars[arg] = dst

    def generate_field(self, function, block, code):
        name = code.refs[0]
        name = name if type(name) == str else block.instructions[name].dest
        ty = self.type_of(function, code)
        src = self.consume_reg(name)
        dst = self.set_reg(code.dest)
        self.code += f'\t; {code.dest} ({dst}) : {ty} = {name}\n\n'
        if dst != src:
            self.add_code('mov', dst, src)

    def generate_dereference(self, function, block, code):
        object = code.refs[0]
        target = object if type(object) == str else block.instructions[object].dest

        self.code += f'\t; &{target}\n'
        dst = self.set_reg(code.dest)
        obj = self.consume_reg(target)
        self.add_code('mov', dst, obj)

        self.code += '\n'
        assert False, 'This requires that we put lvalues into memory'

    def generate_get(self, function, block, code):
        thing_ty = self.types[function.name][code.refs[0]]
        ty = self.type_of(function, code)
        if isinstance(thing_ty, StructType):

            offset = 0
            for n, f in thing_ty.fields.items():
                offset += f.size
                if n == code.refs[1]:
                    break

            src = self.peek_reg(code.refs[0])
            dst = self.set_reg(code.dest)
            self.code += f'\tmov {dst}, [{src} + {thing_ty.size - offset}]\t; {code.dest}: {ty} = {code.refs[0]}.{code.refs[1]}  ({code.refs[0]}: {thing_ty.name})\n'
            self.code += '\n'
        else:
            assert isinstance(ty, LiteralType), "Other's not implemented"

            dst = self.set_reg(code.dest)
            self.add_code('mov', dst, ty.value())
            self.code += '\n'
            # assert False, 'This requires that we put lvalues into memory'

    def generate_assign(self, function, block, code):
        name_a = code.refs[0]
        name_b = code.refs[1]
        target = name_a if type(name_a) == str else block.instructions[name_a].dest
        expr   = name_b if type(name_b) == str else block.instructions[name_b].dest
        dst  = self.consume_reg(target)
        src  = self.consume_reg(expr)
        self.code += f'\t; {target} = {expr}\n\n'
        if type(name_a) != str and block.instructions[name_a].op == Op.INDEX:
            size = self.types[function.name][target].size
            self.add_code('mov', f'[{dst}]', register_to_size(src, size))
        elif dst != src:
            self.add_code('mov', dst, src)

    def generate_index(self, function, block, code):
        object = code.refs[0]
        offset = code.refs[1]

        target = object if type(object) == str else block.instructions[object].dest
        expr   = offset if type(offset) == str else block.instructions[offset].dest

        self.code += f'\t; {target}[{expr}]\n'
        dst = self.set_reg(code.dest)
        obj = self.consume_reg(target)
        self.add_code('mov', dst, obj)

        src = self.consume_reg(expr)
        self.add_code('add', dst, src)

        # Is l-value
        if not code.args[0]:
            self.add_code('mov', dst, f'[{dst}]')

        self.code += '\n'

    def generate_bin(self, function, block, code):
        name_a = code.refs[0]
        name_b = code.refs[1]
        name_a = name_a if type(name_a) == str else block.instructions[name_a].dest
        name_b = name_b if type(name_b) == str else block.instructions[name_b].dest

        a = self.consume_reg(name_a)
        reg = self.set_reg(code.dest)
        b = self.consume_reg(name_b)

        if code.op == Op.ADD:
            if reg != a: self.add_code('mov', reg, a, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
            self.add_code('add',  reg, b, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
        elif code.op == Op.SUB:
            if reg != a: self.add_code('mov', reg, a, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
            self.add_code('sub', reg, b, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
        elif code.op == Op.MUL:
            if reg != a: self.add_code('mov', reg, a, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
            self.add_code('imul', reg, b, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
        elif code.op == Op.DIV:
            self.add_code('push', 'rax')
            self.add_code('push', 'rdx')
            self.add_code('cqo')
            self.add_code('mov', 'rax', a)
            self.add_code('idiv', b, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
            self.add_code('mov', reg, 'rax')
            self.add_code('pop', 'rdx')
            self.add_code('pop', 'rax')
        elif code.op == Op.MOD:
            self.add_code('push', 'rax')
            self.add_code('push', 'rdx')
            self.add_code('cqo')
            self.add_code('mov', 'rax', a)
            self.add_code('idiv', b, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
            self.add_code('mov', reg, 'rdx')
            self.add_code('pop', 'rdx')
            self.add_code('pop', 'rax')
        elif code.op in (Op.EQ, Op.NEQ, Op.LT):
            t = self.set_reg('__temp__')
            self.code += f'\t; {code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}\n'
            self.add_code('cmp',  f'{a}', f'{b}')
            self.add_code('mov',  f'{reg}', '0')
            self.add_code('mov',  f'{t}',   '1')
            self.consume_reg('__temp__')
            # https://www.felixcloutier.com/x86/cmovcc
            if   code.op == Op.EQ:  self.add_code('cmove',  f'{reg}', f'{t}')
            elif code.op == Op.NEQ:  self.add_code('cmovnz', f'{reg}', f'{t}')
            elif code.op == Op.LT:   self.add_code('cmovl',  f'{reg}', f'{t}')
            else:
                assert False
        elif code.op in (Op.AND, Op.OR):
            if reg != a: self.add_code('mov', reg, a, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
            if   code.op == Op.OR:  self.add_code('or',   reg, b, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
            elif code.op == Op.AND: self.add_code('and',  reg, b, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} {code.op} {name_b}')
            else: assert False
        else:
            assert False, f'Not implemented {code}'
        self.code += '\n'

    def generate_lit(self, function, block, code):
        reg = self.set_reg(code.dest)
        t, index, data = code.args
        t = self.type_of(function, code)
        if t.name == 'str' or t.name == 'char*' or t.name.startswith('char['):
            self.add_code('lea', reg, f'[rel data_{index}]', comment=f'{code.dest} : {t} = data_{index} ("{data}")')
        elif t.name == 'real':
            self.add_code('mov', reg, int(data), comment=f'{code.dest} : {t} = {data}')
        # elif type(t) == StructType and t.name == 'struct string':
        #     self.add_code('lea', reg, f'[rel data_{index}]', comment=f'{code.dest} : {t} = data_{index} ("{data}")')
        else:
            # assert t.name != 'inferred'
            self.add_code('mov', reg, data, comment=f'{code.dest} : {t} = {data}')
        self.code += '\n'

    def set_reg(self, name):
        if name in self.vars:
            return self.vars[name]
        for reg in self.regs:
            if reg not in self.mapping.values():
                self.mapping[name] = reg
                return reg
        assert False, "Used up all registers"

    def consume_reg(self, name):
        try:
            if name in self.vars:
                return self.vars[name]
            else:
                return self.mapping.pop(name)
        except KeyError:
            return f'{self.constants[name]}'

    def peek_reg(self, name):
        try:
            if name in self.vars:
                return self.vars[name]
            else:
                return self.mapping[name]
        except KeyError:
            return f'{self.constants[name]}'