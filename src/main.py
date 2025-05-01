from lexer import Lexer
from parser import Parser
from checker import Checker
from generator import Generator
from assembler import make_macho_executable

import sys

def main():
    build = '../examples/'
    name = 'main.sf' if len(sys.argv) < 2 else sys.argv[1]

    source = open(build + name).read()
    tokens = Lexer.lex(source)
    program, data, constants, user_types = Parser.parse_module(tokens, name)
    types  = Checker.check(program, data, constants, user_types)

    code, data = Generator.generate(program, data, constants, types)

    machine_code, readable_code = make_macho_executable(name.split('.')[0], code, data)

    print(readable_code)




if __name__ == '__main__':
    main()
