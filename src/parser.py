from typing import Union, Dict

from lexer import Lexer, Token, TokenStream
from ir import Op, Function, Builtin, Block, Code, Module


class Parser(TokenStream):
    BINARY_OPERATOR = ('+', '-', '*', '.', '&', '/', '%', '|', '^', '~', '!', '<', '>', '==', '!=', 'and', 'or', '<=', '>=', '<<', '>>')
    UNARY_OPERATOR = ('+', '-', '*', '.', '&', 'not')
    PRECEDENCE = {
        # Highest precedence first (levels from Python's operator precedence)
        "as": 19,

        # Operators for function calls, indexing, and attribute access
        # "{": 18,  # Initializer {}
        # "(": 18,  # Function calls ()
        "[": 18,  # Indexing []
        ".": 18,  # Attribute reference .

        # Exponentiation
        "**": 17,  # Exponentiation

        # Unary operators
        "+u": 16,  # Unary positive
        "-u": 16,  # Unary negative
        "~": 16,  # Bitwise NOT

        # Multiplication, division, remainder, and floor division
        "*": 15,  # Multiplication
        "/": 15,  # Division
        "//": 15,  # Floor division
        "%": 15,  # Modulus

        # Addition and subtraction
        "+": 14,  # Addition
        "-": 14,  # Subtraction

        # Bitwise shifts
        "<<": 13,  # Bitwise left shift
        ">>": 13,  # Bitwise right shift

        # Bitwise AND
        "&": 12,  # Bitwise AND

        # Bitwise XOR
        "^": 11,  # Bitwise XOR

        # Bitwise OR
        "|": 10,  # Bitwise OR

        # Comparisons (all have the same precedence)
        "==": 9,  # Equal
        "!=": 9,  # Not equal
        "<": 9,  # Less than
        "<=": 9,  # Less than or equal to
        ">": 9,  # Greater than
        ">=": 9,  # Greater than or equal to
        "is": 9,  # Identity check
        "is not": 9,  # Identity check
        "in": 9,  # Membership check
        "not in": 9,  # Membership check

        # Logical NOT
        "not": 8,  # Logical NOT

        # Logical AND
        "and": 7,  # Logical AND

        # Logical OR
        "or": 6,  # Logical OR

        # Conditional expression (ternary operator)
        "if-else": 5,  # Conditional expressions

        # Assignment operators
        "+=": 4,  # Add AND
        "-=": 4,  # Subtract AND
        "*=": 4,  # Multiply AND
        "/=": 4,  # Divide AND
        "//=": 4,  # Floor Divide AND
        "%=": 4,  # Modulus AND
        "**=": 4,  # Exponent AND
        "&=": 4,  # Bitwise AND
        "|=": 4,  # Bitwise OR
        "^=": 4,  # Bitwise XOR
        ">>=": 4,  # Bitwise Right Shift
        "<<=": 4,  # Bitwise Left Shift

        # Lowest precedence
        # ",": 3,               # Comma (used in function calls, multiple expressions)  TODO: Remove?
        ":": 2,  # Colon (used in slicing, dictionary definition, etc.)
        "lambda": 1  # Lambda expression
    }

    @staticmethod
    def precedence_of(token: Token) -> int:
        return Parser.PRECEDENCE.get(token.kind, -1)

    def __init__(self, tokens: list[Token], name = '__main__'):
        super().__init__(tokens, name)
        self.name = name
        self.functions: Dict[str, Union[Function, Builtin]] = {
            'alloc': Builtin('alloc', [('memory', 'ptr')], {'size': ('int', 0)})
        }
        self.function = None
        self.data = {}
        self.constants = {}
        self.types = {}
        self.imports = {}
        self.in_expression_followed_by_block = False

    def new_function(self, name, is_module=False, is_main=False):
        function = Function(name, is_module=is_module, is_main=is_main)
        self.function = function
        self.functions[name] = function
        block, offset = self.new_block('entry')
        assert offset == 0, "The entry block should always be at offset 0"
        return function, block

    def new_block(self, label):
        block = Block( f'bb{len(self.function.blocks)}_' + label)
        offset = self.function.add(block)
        return block, offset

    def push(self, instruction):
        return self.block.add(instruction)

    @property
    def block(self):
        return self.function.blocks[-1]

    def parse_module_as_import(self, name, imports):
        self.imports = imports
        self.new_function(name, is_module=True)
        while self.has_more():
            self.parse_stmt()
        assert self.block.terminator is None
        self.block.terminator = Code(Op.RET, token=self.peek())
        return self.functions, self.data, self.constants, self.types

    @staticmethod
    def parse_module(tokens, name):
        self = Parser(tokens, name)
        self.new_function(name, is_module=True, is_main=True)
        while self.has_more():
            self.parse_stmt()
        assert self.block.terminator is None
        self.block.terminator = Code(Op.RET, token=self.peek())
        return Module(name, self.functions, self.data, self.constants, self.types, self.imports)

    # TODO: Separate declaration and statements, since a declaration is only allowed
    #       within a module or block.
    def parse_stmt(self):
        t0, t1 = self.peek_many(2)

        if t0.kind == 'ident':
            if t1.kind in (':', ':=', ','):
                return self.parse_decl()
            elif t1.kind == '=':
                ident = self.parse_ident()
                return self.parse_assign(target=ident)
            elif t1.kind == '[':
                ident = self.parse_ident()
                target = self.parse_indexing(ident, is_lvl=True)
                return self.parse_assign(target=target)
            else:
                return self.parse_func_call()
        elif t0.kind == 'if':
            return self.parse_if()
        elif t0.kind == 'while':
            return self.parse_while()
        elif t0.kind == 'return':
            return self.parse_return()
        elif t0.kind == '{':
            return self.parse_block()
        elif t0.kind == '@':
            return self.parse_compiler_attribute()
        elif t0.kind == 'import':
            return self.parse_import()
        else:
            raise RuntimeError(f'Unknown token {t0}')

    def parse_import(self):
        _ = self.next(expect='import')
        things = self.next()
        _ = self.next(expect='from')
        file = self.next(expect='ident').data.decode()

        if file in self.imports:
            functions, data, constants, user_types = self.imports[file]
            self.functions.update(functions)
            self.data.update(data)
            self.constants.update(constants)
            self.types.update(user_types)
            return

        assert things.kind == '*', "Only support full imports for now"
        with open('examples/' + file + '.sf', 'r') as data:
            source = data.read()

        tokens = Lexer.lex(source)
        parser = Parser(tokens, file)
        functions, data, constants, user_types = parser.parse_module_as_import(file + '.sf', self.imports)
        self.functions.update(functions)
        self.data.update(data)
        self.constants.update(constants)
        self.types.update(user_types)

        self.imports[file] = functions, data, constants, user_types


    def parse_decl(self):
        """
        <decl>  ::=  <name> ':' <type> '=' <expr> ';'
        <decl>  ::=  <name> ':=' <expr> ';'
        <decl>  ::=  <name> ':' <type> ';'
        """
        names = [self.next(expect='ident')]
        while self.next_if(','):
            names.append(self.next(expect='ident'))

        if self.next_if(':'):
            type = self.parse_type(names)
            if self.next_if('='):
                expr = self.parse_expr()
                for i, name in enumerate(names):
                    id = self.push(Code(Op.DECL, args=(type, ), dest=name.data.decode(), refs=(expr+i,) if expr is not None else (), token=name))
                return id
            else:
                if hasattr(type, '__iter__'):
                    for t, name in zip(type, names):
                        self.constants[name.data.decode()] = type
                else:
                    for name in names:
                        self.constants[name.data.decode()] = type
        elif self.next_if(':='):
            expr = self.parse_expr()
            if len(names) == 1:
                id = self.push(Code(Op.DECL, dest=names[0].data.decode(), refs=(expr, ) if expr is not None else (), token=names[0]))
            else:
                id = self.push(Code(Op.MULTIDECL, dest=self.implicit_name(), refs=(expr, ) if expr is not None else (), args=tuple(n.data.decode() for n in names), token=names[0]))
            return id
        else:
            raise RuntimeError(f'Unknown token {self.peek()}')

    def parse_assign(self, target):
        assign_token = self.next(expect='=')
        expr = self.parse_expr()
        return self.push(Code(Op.ASSIGN, refs=(target, expr), token=assign_token))

    def parse_if(self):
        if_token = self.next(expect='if')

        # The conditional expression should not be in its own block,
        # as it doesn't create a new label.
        self.in_expression_followed_by_block = True
        condition = self.parse_expr()
        self.in_expression_followed_by_block = False

        # The current block ends the conditional expression and needs
        # to branch to 'then', and 'else'/'end'.
        branch_block = self.block

        # The 'then' block starts the if-body.
        then_block, then_offset = self.new_block('then')

        # The current block ends the if-body, and needs to jump
        # to the 'end', which is over the 'else' body or the next block.
        then_body = self.parse_block()
        end_of_if_body = self.block

        if self.next_if(expect='else'):
            else_block, else_offset = self.new_block('else')
            branch_block.terminator = Code(Op.BR, args=(then_offset, else_offset), refs=(condition, ), token=if_token)

            else_body = self.parse_block()

            end_of_else_block = self.block
            end, end_offset = self.new_block('end')
            end_of_else_block.terminator = Code(Op.JMP, args=(end_offset, ), token=if_token)
        else:
            end, end_offset = self.new_block('end')
            branch_block.terminator = Code(Op.BR, args=(then_offset, end_offset), refs=(condition, ), token=if_token)

        end_of_if_body.terminator = Code(Op.JMP, args=(end_offset, ), token=if_token)

        return then_body


    def parse_while(self):
        while_token = self.next(expect='while')

        # Previous block must jump into the while block.
        previous_block = self.block
        while_condition_entry_block, while_condition_entry_offset = self.new_block('while')
        previous_block.terminator = Code(Op.JMP, args=(while_condition_entry_offset, ), token=while_token)

        # The conditional expression should be in its own block,
        # as it needs a label for the end to jump to.
        self.in_expression_followed_by_block = True
        condition = self.parse_expr()
        self.in_expression_followed_by_block = False

        while_condition_exit_block = self.block

        while_body_entry_block, while_body_entry_offset = self.new_block('then')
        body = self.parse_block()

        while_body_exit_block = self.block
        if while_body_exit_block.terminator is None:
            while_body_exit_block.terminator = Code(Op.JMP, args=(while_condition_entry_offset, ), token=while_token)

        end, end_offset = self.new_block('end')
        while_condition_exit_block.terminator = Code(Op.BR, args=(while_body_entry_offset, end_offset), refs=(condition, ), token=while_token)

        return body

    def parse_return(self):
        return_token = self.next(expect='return')
        args = []
        while True:
            arg = self.parse_expr()
            args.append(arg)
            if not self.next_if(expect=','):
                break
        self.block.terminator = Code(Op.RET, refs=tuple(args), token=return_token)

    def parse_block(self):
        _ = self.next(expect='{')
        stmt = None
        while not self.peek_if_any('}', 'eof'):
            stmt = self.parse_stmt()

        self.next(expect='}')
        return stmt

    def parse_type(self, names):
        assert len(names) == 1
        name = names[0]

        if self.next_if('('):
            t = self.parse_func_decl(name)
        elif token := self.next_if('ident'):
            if token.data.decode() in ('int', 'real', 'string', 'ptr'):
                t = token.data.decode()
            else:
                assert False, 'Not implemented'
        elif token := self.next_if('number'):
            t = int(token.data)
        elif token := self.peek_if('struct'):
            t = self.parse_struct(name.data.decode())
        else:
            assert False, 'Not implemented'

        if token := self.next_if('?'):
            self.types[t+'?'] = { '__optional__': 'optional', 'type': t }
            return t+'?'
        return t

    def parse_func_decl(self, name):
        previous = self.function
        self.new_function(name.data.decode())

        params = {}
        i = 0
        while not self.next_if(expect=')'):
            field = self.next(expect='ident').data.decode()
            field_token = self.next(expect=':')
            type = self.next(expect='ident').data.decode()
            self.next_if(expect=',')
            params[field] = (type, self.push(Code(Op.PARAM, args=(type, ), dest=field, token=field_token)), i)
            i += 1

        returns = []
        if self.next_if('->'):
            i = 0
            while not self.peek_if('{'):
                ret = self.next('ident')
                returns.append((f'ret_{i}', ret.data.decode()))
                self.next_if(',')
                i += 1

        self.function.params = params
        self.function.returns = returns

        self.parse_block()

        if self.block.terminator is None:
            self.block.terminator = Code(Op.RET, token=self.peek())
        self.function = previous
        return 'func'

    def parse_func_call(self):
        name = self.next(expect='ident')
        func = name.data.decode()

        call_token = self.next(expect='(')
        args = []
        while not self.next_if(expect=')'):
            arg = self.parse_expr()
            args.append(arg)
            self.next_if(',')

        call = self.push(Code(Op.CALL, dest=self.implicit_name(), args=(func, ), refs=tuple(args), token=call_token))
        return call

    def parse_struct(self, name: str):
        _ = self.next(expect='struct')
        self.next(expect='{')
        fields = {}
        i = 0
        while not self.next_if(expect='}'):
            field_name = self.next(expect='ident').data.decode()
            self.next(expect=':')
            field_type = self.next(expect='ident').data.decode()
            self.next_if(expect=',')
            fields[field_name] = (field_type, field_name, i)
            i += 1

        self.types[name] = {'__name__': name, **fields}
        return 'struct'

    def parse_initializer(self):
        name = self.next(expect='ident')
        init_token = self.next(expect='{')

        i = 0
        args = []
        while not self.next_if(expect='}'):
            field_name = self.next(expect='ident').data.decode()
            assign_token = self.next(expect='=')
            field_arg = self.parse_expr()
            self.next_if(expect=',')
            add = self.push(Code(Op.FIELD, dest=self.implicit_name(), refs=(field_arg,), args=(None, field_name, i), token=assign_token))
            args.append(add)
            i += 1

        stuff = self.push(Code(Op.INIT, args=(name.data.decode(), ), dest=self.implicit_name(), refs=tuple(args), token=init_token))
        return stuff

    def parse_compiler_attribute(self):
        attribute_token = self.next(expect='@')
        attribute = self.next(expect='ident')
        if attribute.data.decode() == 'syscall':
            self.next(expect='(')

            args = []
            while not self.next_if(expect=')'):
                arg = self.parse_expr()
                args.append(arg)
                self.next_if(',')

            return self.push(Code(Op.SYSCALL, dest=self.implicit_name(), refs=tuple(args), token=attribute_token))
        elif attribute.data.decode() == 'asm':
            self.next(expect='(')
            data = self.parse_string()
            self.next(expect=')')
            return self.push(Code(Op.ASM, dest=self.implicit_name(), refs=(data, ), token=attribute_token))
        else:
            assert False, "Not implemented"

    def parse_indexing(self, target, is_lvl=False):
        index_token = self.next(expect='[')
        expr = self.parse_expr()
        _ = self.next(expect=']')
        return self.push(Code(Op.INDEX, dest=self.implicit_name(), refs=(target, expr), args=(is_lvl, ), token=index_token))

    def parse_expr(self, precedence=0):
        left = self.parse_prefix()

        while self.precedence_of(self.peek()) >= precedence:
            # @NOTE: Special rule for initializer. Otherwise, the statement `if 1+2 {}` will take
            #        `1+2` and parse as a type initialization. Which will always fail since 1+2 is
            #         not a type. The common case is `MyType {}`, which is almost always an identifier.
            #         This is only an issue when in an expression that might be followed by a block,
            #         for example the condition in an if-statement.
            if self.peek_if('{') and (self.previous().kind != 'ident' or self.in_expression_followed_by_block):
                return left

            left = self.parse_infix(left)

        return left

    def parse_prefix(self):
        if op := self.next_if_any(*Parser.UNARY_OPERATOR):
            prec = self.precedence_of(op) + 1
            expr = self.parse_expr(prec)
            match op.kind:
                case '+':
                    return self.push(Code(Op.ADD, dest=self.implicit_name(), refs=(expr,), token=op))
                case '-':
                    return self.push(Code(Op.SUB, dest=self.implicit_name(), refs=(expr,), token=op))
                case '*':
                    return self.push(Code(Op.MUL, dest=self.implicit_name(), refs=(expr,), token=op))
                case '.':
                    return self.push(Code(Op.DOT, dest=self.implicit_name(), refs=(expr,), token=op))
                case '&':
                    return self.push(Code(Op.REF, dest=self.implicit_name(), refs=(expr,), token=op))
                case 'not':
                    return self.push(Code(Op.NOT, dest=self.implicit_name(), refs=(expr,), token=op))
                case _:
                    raise RuntimeError(f'Unknown unary operator {op.kind}')
        elif self.peek_if('number'):
            return self.parse_number()
        elif self.peek_if('real'):
            return self.parse_real()
        elif self.peek_if('string'):
            return self.parse_string()
        elif self.peek_if('ident'):
            if self.peek_many(2)[1].kind == '(':
                return self.parse_func_call()
            if self.peek_many(2)[1].kind == '{' and not self.in_expression_followed_by_block:
                return self.parse_initializer()
            return self.parse_ident()
        elif self.peek_if('none'):
            return self.parse_none()
        elif self.peek_if('@'):
            return self.parse_compiler_attribute()
        elif self.next_if('('):
            node = self.parse_expr()
            self.next(expect=')')
            return node
        else:
            raise RuntimeError(f'Unknown token {self.peek()}')

    def parse_literal(self):
        t = self.peek()
        if t.kind == 'number':
            return self.parse_number()
        elif t.kind == 'real':
            return self.parse_real()
        elif t.kind == 'string':
            return self.parse_string()
        else:
            raise RuntimeError(f'Unknown token {t.kind}')

    def parse_infix(self, left):
        if op := self.next_if_any(*Parser.BINARY_OPERATOR):
            prec = self.precedence_of(op) + 1
            right = self.parse_expr(prec)
            match op.kind:
                case '+':
                    return self.push(Code(Op.ADD, dest=self.implicit_name(), refs=(left, right), token=op))
                case '-':
                    return self.push(Code(Op.SUB, dest=self.implicit_name(), refs=(left, right), token=op))
                case '*':
                    return self.push(Code(Op.MUL, dest=self.implicit_name(), refs=(left, right), token=op))
                case '/':
                    return self.push(Code(Op.DIV, dest=self.implicit_name(), refs=(left, right), token=op))
                case '%':
                    return self.push(Code(Op.MOD, dest=self.implicit_name(), refs=(left, right), token=op))
                case '==':
                    return self.push(Code(Op.EQ, dest=self.implicit_name(), refs=(left, right), token=op))
                case '!=':
                    return self.push(Code(Op.NEQ, dest=self.implicit_name(), refs=(left, right), token=op))
                case '<':
                    return self.push(Code(Op.LT, dest=self.implicit_name(), refs=(left, right), token=op))
                case '>':
                    return self.push(Code(Op.GT, dest=self.implicit_name(), refs=(left, right), token=op))
                case 'and':
                    return self.push(Code(Op.AND, dest=self.implicit_name(), refs=(left, right), token=op))
                case 'or':
                    return self.push(Code(Op.OR, dest=self.implicit_name(), refs=(left, right), token=op))
                case '.':
                    return self.push(Code(Op.ACCESS, dest=self.implicit_name(), refs=(left, right), token=op))
                case _:
                    raise RuntimeError(f'Unknown binary operator {op.kind}')
        elif op := self.peek_if('['):
            return self.parse_indexing(left)
        elif op := self.peek_if('as'):
            return self.parse_cast(left)
        else:
            raise RuntimeError(f'Unknown token {self.peek()}')

    def parse_cast(self, left):
        token = self.next(expect='as')
        t = self.next(expect='ident').data.decode()
        return self.push(Code(Op.AS, args=(t, ), dest=self.implicit_name(), refs=(left,), token=token))

    def parse_number(self):
        token = self.next(expect='number')
        value = token.data
        index = len(self.data)
        self.data[index] = value
        return self.push(Code(Op.LIT, self.implicit_name(), args=('int', index, value), token=token))

    def parse_real(self):
        token = self.next(expect='real')
        value = token.data
        index = len(self.data)
        self.data[index] = value
        return self.push(Code(Op.LIT, self.implicit_name(), args=('real', index, value), token=token))

    def parse_string(self):
        token = self.next(expect='string')
        value = token.data.decode()
        index = len(self.data)
        self.data[index] = value
        return self.push(Code(Op.LIT, self.implicit_name(), args=('str', index, value), token=token))

    def parse_none(self):
        token = self.next(expect='none')
        index = len(self.data)
        self.data[index] = token
        return self.push(Code(Op.LIT, self.implicit_name(), args=('none', 0, 0), token=token))

    def parse_ident(self):
        """Name referring to an existing value"""
        name = self.next(expect='ident').data.decode()
        return name  # self.block.declarations[name] if name in self.block.declarations else name

    ID = -1
    def implicit_name(self):
        Parser.ID += 1
        return f'var_{Parser.ID}'





















