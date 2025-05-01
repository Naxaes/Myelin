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
    module = Parser.parse_module(tokens, name)
    types  = Checker.check(module)

    code, data = Generator.generate(module, types)

    machine_code, readable_code = make_macho_executable(name.split('.')[0], code, data)

    for func in module.functions.values():
        print(f'{func}')
        for b in func.blocks:
            print(f'\t{b}')
            for instruction in b.instructions:
                print(f'\t\t{instruction}')
            print(f'\t\t{b.terminator}')

    # print(readable_code)
    with open(f'build/{name.replace(".sf", "")}', 'wb') as file:
        file.write(machine_code)




if __name__ == '__main__':
    main()
