from typing import Union, Dict

from lexer import Lexer, Token, TokenStream
from ir.basic_block import Block, Code
from ir.function import Function


class Builtin:
    def __init__(self, name, returns, params):
        self.name = name
        self.returns = returns
        self.params = params
        self.blocks = []

    def __repr__(self):
        parameters = ', '.join(f'{x}: {t[0]}' for x, t in self.params.items())
        rets = ', '.join(ty for name, ty in self.returns)
        return f'{self.name}: @builtin({parameters}) -> {rets or "void"}'


class Module:
    def __init__(self, name, functions, data, constants, types, imports):
        self.name = name
        self.functions = functions
        # Static data needed in the executable
        self.data = data
        # Constants inlined in the code
        self.constants = constants
        self.types = types
        self.imports = imports


class Parser(TokenStream):
    """
    <stmt> ::= <decl>
            | <assign>
            | <call>
            | <if>
            | <while>
            | <switch>
            | <block>
            | <return>
            | <continue>
            | <break>

    <expr> ::= <func>
            | <type>
            | <if>
            | <while>
            | <switch>
            | <block>
            | <call>
            | <init>
            | <index>
            | <binary>
            | <unary>
            | <ident>
            | <literal>

    <decl> ::= <name> ':' <expr> '=' <expr>
             | <name> ':' <expr>
             | <name> ':=' <expr>

    <assi> ::= <expr> '=' <expr>
             | <expr> '[' <arg-list> ']'
             | <expr> '.' <expr> ['.' <expr>]*          # Problematic if expr can be used as start (?)

    <call> ::= <expr> '(' [<arg-list>] ')'              # Problematic if expr can be used as start, then '(' is a valid start token
    <init> ::= <name> '{' [<arg-list>] '}'              # Problematic as '{' is a valid start token for block

    <return>   ::= 'return'   [<expr> [',' <expr>]]     # Problematic as we don't know if expr is a new expression or part of the keyword
    <continue> ::= 'continue' [<expr> [',' <expr>]]     # Problematic as we don't know if expr is a new expression or part of the keyword
    <break>    ::= 'break'    [<expr> [',' <expr>]]     # Problematic as we don't know if expr is a new expression or part of the keyword

    <func> ::= 'func' '(' [<param-list>] ')' ['->' <ret-list>] [<block>]
    <type> ::= 'type' '{' [<field-list>] '}'
    """
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
        super().__init__(tokens)
        self.name = name
        self.functions: Dict[str, Union[Function, Builtin]] = {
            'alloc': Builtin('alloc', [('memory', 'ptr')], {'size': ('int', 0)})
        }
        self.current = None
        self.data = {}
        self.constants = {}
        self.types = {}
        self.imports = {}
        self.in_expression_followed_by_block = False

    def new_function(self, name, params, is_module=False, is_main=False):
        function = Function(name, params, is_module=is_module, is_main=is_main)
        self.functions[name] = function
        self.current = function
        self.new_block('entry')
        return function

    def new_block(self, label):
        block = Block(label, len(self.current.blocks))
        self.current.blocks.append(block)
        return block

    def push(self, instruction):
        id = len(self.block.instructions)
        self.block.instructions.append(instruction)
        return id

    @property
    def block(self):
        return self.current.blocks[-1] if len(self.current.blocks) > 0 else None

    def parse_module_as_import(self, name, imports):
        self.imports = imports
        self.new_function(name, [], is_module=True)
        while self.has_more():
            self.parse_stmt()
        self.block.terminator = Code('ret')
        return self.functions, self.data, self.constants, self.types

    @staticmethod
    def parse_module(tokens, name):
        self = Parser(tokens, name)
        self.new_function(name, [], is_module=True, is_main=True)
        while self.has_more():
            self.parse_stmt()
        self.block.terminator = Code('ret')
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
                self.parse_func_call()
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
            program, data, constants, user_types = self.imports[file]
            self.functions.update(program)
            self.data.update(data)
            self.constants.update(constants)
            self.types.update(user_types)
            return

        assert things.kind == '*', "Only support full imports for now"
        with open('examples/' + file + '.sf', 'r') as data:
            source = data.read()

        tokens = Lexer.lex(source)
        parser = Parser(tokens, file)
        program, data, constants, user_types = parser.parse_module_as_import(file + '.sf', self.imports)
        self.functions.update(program)
        self.data.update(data)
        self.constants.update(constants)
        self.types.update(user_types)

        self.imports[file] = program, data, constants, user_types


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
                    id = self.push(Code('decl', type, dest=name.data.decode(), refs=(expr+i,) if expr is not None else ()))
                    # self.block.declarations[name.data.decode()] = id
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
                id = self.push(Code('decl', dest=names[0].data.decode(), refs=(expr, ) if expr is not None else ()))
            else:
                id = self.push(Code('multidecl', dest=self.implicit_name(), refs=(expr, ) if expr is not None else (), args=tuple(n.data.decode() for n in names)))
                # self.block.declarations[name.data.decode()] = id
        else:
            raise RuntimeError(f'Unknown token {self.peek()}')

    def parse_assign(self, target):
        _ = self.next(expect='=')
        expr = self.parse_expr()
        return self.push(Code('assign', refs=(target, expr)))

    def parse_if(self):
        _ = self.next(expect='if')

        self.in_expression_followed_by_block = True
        cond = self.parse_expr()
        self.in_expression_followed_by_block = False

        prev = self.block
        then = self.new_block('then')
        body = self.parse_block()

        elze = None
        if self.next_if(expect='else'):
            elze  = self.new_block('else')
            other = self.parse_block()

        end = self.new_block('end')

        prev.terminator = Code('br', args=(then.offset, elze.offset if elze else end.offset), refs=(cond, ))

        if then.terminator is None:
            then.terminator = Code('jmp', args=(end.offset,))
        if elze and elze.terminator is None:
            elze.terminator = Code('jmp', args=(elze.offset + 1,))

    def parse_while(self):
        _ = self.next(expect='while')

        prev = self.block
        whyle = self.new_block('while')
        prev.terminator = Code('jmp', args=(whyle.offset,))

        self.in_expression_followed_by_block = True
        cond = self.parse_expr()
        self.in_expression_followed_by_block = False

        prev = self.block

        then = self.new_block('then')
        body = self.parse_block()

        then.terminator = Code('jmp', args=(whyle.offset,))
        end = self.new_block('end')

        prev.terminator = Code('br', args=(then.offset, end.offset), refs=(cond, ))

    def parse_return(self):
        _ = self.next(expect='return')
        args = []
        while True:
            arg = self.parse_expr()
            args.append(arg)
            if not self.next_if(expect=','):
                break
        self.block.terminator = Code('ret', refs=tuple(args))

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
            return self.parse_func_decl(name)
        elif token := self.next_if('ident'):
            if token.data.decode() in ('int', 'real', 'string', 'ptr'):
                return token.data.decode()
            assert False, 'Not implemented'
        elif token := self.next_if('number'):
            return int(token.data)
        elif token := self.peek_if('struct'):
            return self.parse_struct(name.data.decode())
        else:
            assert False, 'Not implemented'

    def parse_func_decl(self, name):
        previous = self.current
        self.new_function(name.data.decode(), {})
        params = {}
        i = 0
        while not self.next_if(expect=')'):
            field = self.next(expect='ident').data.decode()
            self.next(expect=':')
            type = self.next(expect='ident').data.decode()
            self.next_if(expect=',')
            params[field] = (type, self.push(Code('param', type=type, dest=field)), i)
            i += 1
        self.current.params = params
        returns = []
        if self.next_if('->'):
            i = 0
            while not self.peek_if('{'):
                ret = self.next('ident')
                returns.append((f'ret_{i}', ret.data.decode()))
                self.next_if(',')
                i += 1
        self.current.returns = returns
        self.parse_block()
        if self.block.terminator is None:
            self.block.terminator = Code('leave')
        self.current = previous
        return 'func'

    def parse_func_call(self):
        name = self.next(expect='ident')
        func = name.data.decode()

        self.next(expect='(')
        args = []
        while not self.next_if(expect=')'):
            arg = self.parse_expr()
            args.append(arg)
            self.next_if(',')

        call = self.push(Code('call', dest=self.implicit_name(), args=(func, ), refs=tuple(args)))
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
        _ = self.next(expect='{')

        i = 0
        args = []
        while not self.next_if(expect='}'):
            field_name = self.next(expect='ident').data.decode()
            self.next(expect='=')
            field_arg = self.parse_expr()
            self.next_if(expect=',')
            add = self.push(Code('field', dest=self.implicit_name(), refs=(field_arg,), args=(field_name, i)))
            args.append(add)
            i += 1

        stuff = self.push(Code('init', type=name.data.decode(), dest=self.implicit_name(), refs=tuple(args)))
        return stuff


    def parse_compiler_attribute(self):
        _ = self.next(expect='@')
        attribute = self.next(expect='ident')
        if attribute.data.decode() == 'syscall':
            self.next(expect='(')

            args = []
            while not self.next_if(expect=')'):
                arg = self.parse_expr()
                args.append(arg)
                self.next_if(',')

            return self.push(Code('syscall', type='int', dest=self.implicit_name(), refs=tuple(args)))
        elif attribute.data.decode() == 'asm':
            self.next(expect='(')
            data = self.parse_string()
            self.next(expect=')')
            return self.push(Code('asm', dest=self.implicit_name(), refs=(data, )))
        else:
            assert False, "Not implemented"

    def parse_indexing(self, target, is_lvl=False):
        _ = self.next(expect='[')
        expr = self.parse_expr()
        _ = self.next(expect=']')
        return self.push(Code('index', dest=self.implicit_name(), refs=(target, expr), args=(is_lvl, )))

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
            return self.push(Code(op.kind, dest=self.implicit_name(), refs=(expr,)))
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

    def parse_infix(self, left):
        if op := self.next_if_any(*Parser.BINARY_OPERATOR):
            prec = self.precedence_of(op) + 1
            right = self.parse_expr(prec)
            return self.push(Code(op.kind, dest=self.implicit_name(), refs=(left, right)))
        elif op := self.peek_if('['):
            return self.parse_indexing(left)
        elif op := self.peek_if('as'):
            return self.parse_cast(left)
        else:
            raise RuntimeError(f'Unknown token {self.peek()}')

    def parse_cast(self, left):
        _ = self.next(expect='as')
        t = self.next(expect='ident').data.decode()
        return self.push(Code('as', type=t, dest=left, refs=(left,)))

    def parse_number(self):
        value = self.next(expect='number').data
        index = len(self.data)
        self.data[index] = value
        return self.push(Code('lit', 'int', self.implicit_name(), args=(index, value)))

    def parse_real(self):
        value = self.next(expect='real').data
        index = len(self.data)
        self.data[index] = value
        return self.push(Code('lit', 'real', self.implicit_name(), args=(index, value)))

    def parse_string(self):
        value = self.next(expect='string').data.decode()
        index = len(self.data)
        self.data[index] = value
        return self.push(Code('lit', 'str', self.implicit_name(), args=(index, value)))

    def parse_ident(self):
        """Name referring to an existing value"""
        name = self.next(expect='ident').data.decode()
        return name  # self.block.declarations[name] if name in self.block.declarations else name

    ID = -1
    def implicit_name(self):
        Parser.ID += 1
        return f'var_{Parser.ID}'





















