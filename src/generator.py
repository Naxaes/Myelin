class Generator:
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

    def type_of(self, function, code):
        return self.types[function.name][code.dest]

    @staticmethod
    def generate(functions, data, constants, types):
        self = Generator(functions, data, constants, types)
        for name, function in self.functions.items():
            if len(function.blocks) == 0:
                continue
            self.code += f"; -------- '{name}' --------\n{name}:\n"
            self.mapping = { }
            self.vars    = { }
            for block in function.blocks:
                self.mapping = self.vars.copy()
                self.code += f'.{block.label}_{block.offset}:\n'
                for code in block.instructions:
                    if code.op == 'lit':
                        self.generate_lit(function, block, code)
                    elif code.op in ('+', '*', '==', '<'):
                        self.generate_bin(function, block, code)
                    elif code.op == 'decl':
                        self.generate_decl(function, block, code)
                    elif code.op == 'assign':
                        self.generate_assign(function, block, code)
                    elif code.op == 'label':
                        self.code += f'.{code.args[0]}:\n'
                    elif code.op == 'call':
                        self.generate_call(function, block, code)
                    elif code.op == 'param':
                        self.generate_param(code)
                    elif code.op == '_':
                        # Pseudo-target
                        pass
                    elif code.op == 'field':
                        self.generate_decl(function, block, code)
                    elif code.op == 'init':
                        self.generate_decl(function, block, code)
                    elif code.op == 'syscall':
                        self.generate_syscall(function, block, code)
                    elif code.op == 'index':
                        self.generate_index(function, block, code)
                    elif code.op == '&':
                        self.generate_dereference(function, block, code)
                    elif code.op == 'as':
                        pass
                    elif code.op == '.':
                        self.generate_get(function, block, code)
                    else:
                        assert False, f'Unknown instruction {code}'

                code = block.terminator
                if code.op == 'br':
                    self.generate_ite(function, block, code)
                elif code.op == 'jmp':
                    self.generate_jmp(function, block, code)
                elif code.op == 'ret':
                    self.generate_ret(function, block, code)
                else:
                    assert False, f"Unknown terminator {code}"

        data = ""
        for i, d in self.data.items():
            if type(d) == str:
                data += f'data_{i}: db `{d}`, 0\n'

        return self.code, data

    def add_code(self, *args, comment=None):
        if len(args) == 3:
            a = args[1]+',' if len(args[1]) == 3 else args[1]+', '
            self.code += f'\t{args[0]:<5} {a:<3} {args[2]:<3}'
        elif len(args) == 2:
            self.code += f'\t{args[0]:<5} {args[1]:<7}'
        elif len(args) == 1:
            self.code += f'\t{args[0]:<13}'
        else:
            assert False
        if comment: self.code += f'\t\t; {comment}'
        self.code += '\n'

    def generate_jmp(self, function, block, code):
        if code.args[0] != block.offset + 1:  # No need to jump to next block.
            block = function.blocks[code.args[0]]
            self.add_code('jmp', f'.{block.label}_{block.offset}')
            self.code += '\n'

    def generate_param(self, code):
        param = code.dest
        dst = self.set_reg(param)
        self.code += f'\t; {param} := {dst}\n\n'
        self.vars[code.dest] = dst

    def generate_call(self, function, block, code):
        func = code.args[0]
        pushed = self.prepare_function_call(function, block, code)
        self.add_code('call', func.name)
        self.finish_function_call(code, pushed, len(func.returns))

    def generate_syscall(self, function, block, code):
        pushed = self.prepare_function_call(function, block, code)
        self.add_code('syscall')
        self.finish_function_call(code, pushed, returns = 1)

    def finish_function_call(self, code, pushed, returns = 0):
        for i in range(returns):
            dest = code.dest if i == 0 else f'{code.dest[:4]}{int(code.dest[4:]) + i}'
            dst = self.set_reg(dest)
            self.add_code('mov', dst, self.regs[i])
        for reg in reversed(pushed):
            self.add_code('pop', reg)
        self.code += '\n'

    def prepare_function_call(self, function, block, code):
        assert code.op == 'call' or code.op == 'syscall'

        pushed = []
        for i, n in enumerate(self.regs):
            if n in self.vars.values():
                self.add_code('push', n)
                pushed.append(n)
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
            self.add_code('mov', 'rdi', list(self.mapping.values())[-1])
            self.add_code('mov', 'rax', '0x2000000+1')
            self.add_code('syscall')
            self.code += '\n'
        elif function.is_module:
            pass
        else:
            self.add_code('ret')
            self.code += '\n'

    def generate_ite(self, function, block, code):
        cond = block.instructions[code.refs[0]].dest
        left = function.blocks[code.args[0]]
        right = function.blocks[code.args[1]]
        src = self.consume_reg(cond)
        self.add_code('test', src, src)
        self.add_code('je', f'.{right.label}_{right.offset}', comment=f'{cond}')
        self.code += '\n'

    def generate_decl(self, function, block, code):
        if self.type_of(function, code).name == 'func':
            return

        name = code.refs[0]
        name = name if type(name) == str else block.instructions[name].dest
        src = self.consume_reg(name)
        dst = self.set_reg(code.dest)
        self.code += f'\t; {code.dest} ({dst}) : {self.type_of(function, code)} = {name}\n\n'
        if dst != src:
            self.add_code('mov', dst, src)
        self.vars[code.dest] = dst

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
        t = self.type_of(function, code)
        # assert isinstance(t, LiteralType), "Other's not implemented"

        dst = self.set_reg(code.dest)
        self.add_code('mov', dst, t.value())
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
        if type(name_a) != str and block.instructions[name_a].op == 'index':
            self.add_code('mov', f'[{dst}]', src)
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

        if code.op == '+':
            if reg != a: self.add_code('mov', reg, a, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} + {name_b}')
            self.add_code('add',  reg, b, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} + {name_b}')
        elif code.op == '*':
            if reg != a: self.add_code('mov', reg, a, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} * {name_b}')
            self.add_code('imul', reg, b, comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} * {name_b}')
        elif code.op in ('==', '<'):
            t = self.set_reg('__temp__')
            self.add_code('cmp',  f'{a}', f'{b}', comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} == {name_b}')
            self.add_code('mov',  f'{reg}', '0')
            self.add_code('mov',  f'{t}',   '1')
            self.consume_reg('__temp__')
            if   code.op == '==':  self.add_code('cmove', f'{reg}', f'{t}', comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} == {name_b}')
            elif code.op == '<':   self.add_code('cmovl', f'{reg}', f'{t}', comment=f'{code.dest} : {self.type_of(function, code)} = {name_a} == {name_b}')
            else:
                assert False
        else:
            assert False, f'Not implemented {code}'
        self.code += '\n'

    def generate_lit(self, function, block, code):
        reg = self.set_reg(code.dest)
        index, data = code.args
        if self.type_of(function, code).name == 'str' or self.type_of(function, code).name == 'byte*' or self.type_of(function, code).name.startswith('byte['):
            self.add_code('mov', reg, f'data_{index}', comment=f'{code.dest} : {self.type_of(function, code)} = data_{index} ("{data}")')
        elif self.type_of(function, code).name == 'real':
            self.add_code('mov', reg, int(data), comment=f'{code.dest} : {self.type_of(function, code)} = {data}')
        else:
            self.add_code('mov', reg, data, comment=f'{code.dest} : {self.type_of(function, code)} = {data}')
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