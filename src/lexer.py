from typing import Any, Optional

TOKENS1 = {
    # Arithmetic operators
    '+', '-', '*', '/', '%',

    # Bitwise operators
    '&', '|', '^', '~',

    # Logical operators
    '!',

    # Comparison operators
    '<', '>',

    # Assignment operator
    '=',

    # Punctuation
    ',', ';', ':', '?', '.',

    # Brackets
    '(', ')', '[', ']', '{', '}',

    # Other
    '#', '$', '@'
}
TOKENS2 = {
    # Arithmetic and assignment operators
    '+=', '-=', '*=', '/=', '%=', '++', '--',

    # Logical and comparison operators
    '==', '!=', '&&', '||', '<=', '>=',

    # Bitwise operators
    '<<', '>>', '&=', '|=', '^=',

    # Digraphs
    '<:', ':>', '<%', '%>', '%:',

    # Other tokens
    '->', ':='
}

KEYWORDS = {
    "and",
    "as",
    "auto",
    "break",
    "case",
    "const",
    "continue",
    "default",
    "do",
    "else",
    "enum",
    "extern",
    "for",
    "from",
    "goto",
    "if",
    "import",
    "is",
    "inline",
    "or",
    "register",
    "restrict",
    "return",
    "static",
    "struct",
    "switch",
    "then",
    "union",
    "volatile",
    "when",
    "where",
    "while"
}


class Location:
    Self = 'Location'

    def __init__(self, index: int, row: int, col: int):
        self.index = index
        self.row = row
        self.col = col

    def next(self, char: str) -> Self:
        return self.next_row() if char == '\n' else self.next_col()

    def next_row(self) -> Self:
        return Location(self.index + 1, self.row + 1, 1)

    def next_col(self, count=1) -> Self:
        return Location(self.index + count, self.row, self.col + count)

    def __repr__(self):
        return f'Location(index={self.index}, row={self.row}, col={self.col})'


class Token:
    KIND_WITH_DATA = {'ident', 'string', 'number', 'real'}

    KIND = {*TOKENS1, *TOKENS2, *KEYWORDS, *KIND_WITH_DATA}

    def __init__(self, kind: str, begin: Location, end: Location, data: Any = None):
        self.kind = kind
        self.begin = begin
        self.end = end
        self.data = data

    def str(self):
        if self.kind in Token.KIND_WITH_DATA:
            name = self.kind.title()
        else:
            name = f"'{self.kind}'"

        if self.data:
            return f'{name}({self.data}) @ {self.begin.row}:{self.begin.col}'
        else:
            return f'{name} @ {self.begin.row}:{self.begin.col}'

    def __repr__(self):
        if self.kind in ('ident', 'string'):
            return f'Tok({self.data.decode("utf-8")})'
        elif self.kind in ('number', 'real'):
            return f'Tok({self.data})'
        return f'Tok({self.kind})'


def is_ident_start(char: str) -> bool:
    return char.isalpha() or char == '_'


def is_ident_cont(char: str) -> bool:
    return char.isalpha() or char == '_' or char.isnumeric()


class Lexer:
    MATCHING_DELIMITER = {
        '(': ')',
        '{': '}',
        '[': ']',
        ')': '(',
        '}': '{',
        ']': '[',
    }

    def __init__(self, source: str):
        self.source = source
        self.tokens = []

        self.location = Location(0, 1, 1)

        self.expected_delimiter = []
        self.delimiter = {
            '(': 0,
            '{': 0,
            '[': 0,
        }

    def repr_of(self, begin: Location, end: Location) -> str:
        return self.source[begin.index:end.index]

    def peek(self) -> tuple[str, Location]:
        if self.location.index >= len(self.source):
            return '', self.location

        char = self.source[self.location.index]
        return char, self.location

    def next(self) -> tuple[str, Location]:
        char, previous = self.peek()
        self.location = self.location.next(char)
        return char, previous

    def skip_whitespace(self, char: str, begin: Location) -> tuple[str, Location]:
        while char in ('\t', ' ', '\n'):
            char, begin = self.next()
        return char, begin

    def lex_identifier(self, char: str, begin: Location) -> tuple[str, Location]:
        assert is_ident_start(char)

        end = begin
        while is_ident_cont(char):
            char, end = self.next()

        text = self.repr_of(begin, end)
        if text in KEYWORDS:
            self.tokens.append(Token(text, begin, end))
        else:
            self.tokens.append(Token('ident', begin, end, bytes(text, 'utf-8')))
        return char, end

    def lex_number(self, char: str, begin: Location) -> tuple[str, Location]:
        assert char.isnumeric()
        end = begin

        if char == '0':
            char, end = self.next()
            if char == 'x':
                char, end = self.next()
                while char.isnumeric() or char in 'ABCDEF' or char in 'abcdef':
                    char, end = self.next()
                self.tokens.append(Token('number', begin, end, int(self.repr_of(begin, end), 16)))
                return char, end
            else:
                pass

        while char.isnumeric():
            char, end = self.next()

        has_period = False
        if char == '.':
            has_period = True
            char, end = self.next()
            while char.isnumeric():
                char, end = self.next()

        if has_period:
            self.tokens.append(Token('real', begin, end, float(self.repr_of(begin, end))))
        else:
            self.tokens.append(Token('number', begin, end, int(self.repr_of(begin, end))))
        return char, end

    def lex_string(self, char: str) -> tuple[str, Location]:
        assert char == '"'

        char, begin = self.next()
        end = begin
        while char not in ('"', '\n', ''):
            char, end = self.next()

        if char != '"':
            raise RuntimeError(f"Missing close quotation, got {repr(char)}")

        # NOTE: Don't include '"' in the data or location.
        self.tokens.append(Token('string', begin, end, bytes(self.repr_of(begin, end), 'utf-8')))
        return self.next()

    def lex_and_record_opening_delimiter(self, char: str, begin: Location) -> tuple[str, Location]:
        assert char in ('(', '{', '[')
        self.delimiter[char] += 1
        self.expected_delimiter.append(Lexer.MATCHING_DELIMITER[char])
        self.tokens.append(Token(char, begin, self.location))
        return self.next()

    def lex_and_record_closing_delimiter(self, char: str, begin: Location) -> tuple[str, Location]:
        assert char in (')', '}', ']')

        if char != (expected_delimiter := self.expected_delimiter.pop()):
            raise RuntimeError(f'Delimiter {char} does not match delimiter {expected_delimiter} @ {begin}')

        starting_delimiter = Lexer.MATCHING_DELIMITER[char]
        if self.delimiter[starting_delimiter] == 0:
            raise RuntimeError(f'Delimiter {char} does not have a matching {starting_delimiter} @ {begin}')

        self.delimiter[starting_delimiter] -= 1
        self.tokens.append(Token(char, begin, self.location))
        return self.next()

    @staticmethod
    def lex(source) -> list[Token]:
        self = Lexer(source)

        char, begin = self.next()
        while char:
            if char in ('\t', ' ', '\n'):
                char, begin = self.skip_whitespace(char, begin)

            elif is_ident_start(char):
                char, begin = self.lex_identifier(char, begin)

            elif char.isnumeric():
                char, begin = self.lex_number(char, begin)

            elif char == '"':
                char, begin = self.lex_string(char)

            elif char in ('(', '{', '['):
                char, begin = self.lex_and_record_opening_delimiter(char, begin)

            elif char in (')', '}', ']'):
                char, begin = self.lex_and_record_closing_delimiter(char, begin)

            elif char == '#':
                char, end = self.next()
                while char not in ('\n', ''):
                    char, begin = self.next()

            else:
                char2, end = self.peek()

                symbol = char + char2
                if symbol == '#':
                    char, end = self.next()
                    while char not in ('\n', ''):
                        char, begin = self.next()
                elif symbol == '/*':
                    char2, end = self.next()
                    while char + char2 != '*/' and char2 != '':
                        char = char2
                        char2, begin = self.next()
                if symbol in TOKENS2:
                    _, end = self.next()
                    self.tokens.append(Token(symbol, begin, end))
                    char, begin = self.next()
                elif char in TOKENS1:
                    self.tokens.append(Token(char, begin, self.location))
                    char, begin = self.next()
                else:
                    raise RuntimeError(f'Invalid token {char}')

        if len(self.expected_delimiter) != 0:
            raise RuntimeError('Missing delimiters ' + ', '.join(self.expected_delimiter))

        end = self.location
        self.tokens.append(Token('eof', begin, end))

        return self.tokens


class TokenStream:
    def __init__(self, tokens):
        self.__current = 0
        self.__tokens = tokens

    def previous(self):
        if self.__current == 0:
            return None
        return self.__tokens[self.__current - 1]

    def previous_is(self, kind):
        return self.previous() and self.previous().kind == kind

    def peek_many(self, count=1) -> list[Token]:
        tokens = self.__tokens[self.__current:self.__current + count]
        return tokens

    def peek(self) -> Token:
        token = self.__tokens[self.__current]
        return token

    def peek_if(self, expected) -> bool:
        return self.peek().kind == expected

    def peek_if_any(self, *expected) -> bool:
        token = self.peek()
        return any(token.kind == e for e in expected)

    def peek_if_all(self, *expected) -> bool:
        count = len(expected)
        tokens = self.peek_many(count)
        if all(t.kind == e for t, e in zip(tokens, expected)):
            return True
        return False

    def next(self, expect=None) -> Token:
        token = self.peek()
        if expect and expect != token.kind:
            raise RuntimeError(f'Expected {expect}, got unexpected token {token}')
        if token.kind != 'eof':
            self.__current += 1
        return token

    def next_if(self, expect) -> Optional[Token]:
        token = self.peek()
        if expect != token.kind:
            return None
        if token.kind != 'eof':
            self.__current += 1
        return token

    def next_if_any(self, *expects) -> Optional[Token]:
        token = self.peek()
        if token.kind in expects:
            self.__current += 1
            return token
        return None

    def next_if_all(self, *expects) -> list[Optional[Token]]:
        count = len(expects)
        tokens = self.peek_many(count)
        if all(t.kind == e for t, e in zip(tokens, expects)):
            self.__current += count
            return tokens
        return [None] * count

    def is_on_same_line(self, token: Token) -> bool:
        if not self.has_more():
            return True
        else:
            return token.end.row == self.peek().begin.row

    def has_more(self) -> bool:
        return self.__current + 1 < len(self.__tokens)


def main():
    source = """
    a := 10 + 10 * 2
    b := 33

    do_things: () {  }
    # do_things: (x: int, y: int) -> int { 10 + 10 }
    """

    tokens = Lexer.lex(source)
    print(tokens)




if __name__ == '__main__':
    main()
