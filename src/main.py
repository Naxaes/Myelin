from lexer import Lexer
from parser import Parser
from checker import Checker
from x86_64_generator import X86_64_Generator
from ir.passes import remove_unused_functions
from assembler import make_macho_executable

from pathlib import Path
import sys


def main():
    build = '../examples/'
    path = Path('main.sf' if len(sys.argv) < 2 else sys.argv[1])

    source = open(build + path.name).read()
    tokens = Lexer.lex(source)
    module = Parser.parse_module(tokens, path.name)
    types  = Checker.check(module)

    remove_unused_functions(module)

    code, data = X86_64_Generator.generate(module, types)
    machine_code, readable_code = make_macho_executable(path.stem, code, data)

    for func in module.functions.values():
        print(f'{func}')
        for b in func.blocks:
            print(f'\t{b}')
            for i, instruction in enumerate(b.instructions):
                print(f'\t\t[{i:02}]: {instruction}')
            print(f'\t\t[{len(b.instructions):02}]: {b.terminator}')

    # print(readable_code)
    with open(f'build/{path.stem}', 'wb') as file:
        file.write(machine_code)




if __name__ == '__main__':
    main()
