#!/usr/bin/env python3

from lexer import Lexer
from parser import Parser
from ssa import check_if_in_ssa_form
from type_checker import TypeChecker
from x86_64_generator import X86_64_Generator
from ir.ir_parser import parse
from ir.passes import remove_unused_functions
from assembler import make_macho_executable

from pathlib import Path
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='Run just type checking', default=True)
    parser.add_argument('--check', help='Run semantic analysis', action='store_true')
    parser.add_argument('--run', help='Run the executable', action='store_true')
    parser.add_argument('--is-ir', help='Assume the file is in ir format', action='store_true')

    args = parser.parse_args()

    path = Path(args.file)

    source = open(path).read()
    if args.is_ir:
        module = parse(source)
    else:
        tokens = Lexer.lex(source)
        module = Parser.parse_module(tokens, path.name)

    types = TypeChecker.check(module)
    if not check_if_in_ssa_form(module):
        raise ValueError("Module is not in SSA form. Please run the SSA pass before type checking.")

    # print(module)

    if args.check:
        return  # Exit after type checking

    remove_unused_functions(module)

    code, data = X86_64_Generator.generate(module, types)
    machine_code, readable_code = make_macho_executable(path.stem, code, data)

    with open(f'build/{path.stem}', 'wb') as file:
        file.write(machine_code)

    if args.run:
        import subprocess
        process = subprocess.run([f'build/{path.stem}'])
        print(f'Exit status: {process.returncode}')




if __name__ == '__main__':
    main()
