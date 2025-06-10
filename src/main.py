#!/usr/bin/env python3
from ir.passes import generate_graph_viz
from lexer import Lexer
from parser import Parser
from ssa import check_if_in_ssa_form
from type_checker import TypeChecker
from x86_64_generator import X86_64_Generator
from ir import parse, validate_ir, remove_unused_functions
from assembler import make_macho_executable

from pathlib import Path
import argparse
import subprocess


def repl():
    repl_code = 'import * from macos\nimport * from core\n'
    output = ''
    while True:
        line = input('> ')

        source = repl_code + line + '\n'

        try:
            tokens = Lexer.lex(source)
            module = Parser.parse_module(source, tokens, 'repl')
            types = TypeChecker.check(module)

            validate_ir(module)
            check_if_in_ssa_form(module)
            remove_unused_functions(module)

            code, data = X86_64_Generator.generate(module, types)
            machine_code, readable_code = make_macho_executable('repl', code, data)
            with open(f'build/repl', 'wb') as file:
                file.write(machine_code)

            process = subprocess.run([f'build/repl'], capture_output=True)
            if process.stdout:
                new_output = str(process.stdout)[2:-3]
                print(new_output.removeprefix(output))
                output = new_output
            repl_code = source
        except Exception as e:
            print(f'[ERROR]: {e}')



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='Source code file')
    parser.add_argument('--check', help='Run semantic analysis', action='store_true')
    parser.add_argument('--run', help='Run the executable', action='store_true')
    parser.add_argument('--is-ir', help='Assume the file is in ir format', action='store_true')

    args = parser.parse_args()

    if args.file == 'repl':
        return repl()

    path = Path(args.file)

    source = open(path).read()
    if args.is_ir or path.suffix == '.ir':
        module = parse(source)
    else:
        tokens = Lexer.lex(source)
        module = Parser.parse_module(source, tokens, path.name)
        validate_ir(module)

    types = TypeChecker.check(module)
    if not check_if_in_ssa_form(module):
        raise ValueError("Module is not in SSA form. Please run the SSA pass before type checking.")

    if args.check:
        return None

    remove_unused_functions(module)
    graph_vis_source = generate_graph_viz(module)
    with open(f'build/{path.stem}.dot', 'wb') as file:
        file.write(graph_vis_source.encode())

    # print(module)

    code, data = X86_64_Generator.generate(module, types)
    machine_code, readable_code = make_macho_executable(path.stem, code, data)

    with open(f'build/{path.stem}', 'wb') as file:
        file.write(machine_code)

    if args.run:
        process = subprocess.run([f'build/{path.stem}'])
        exit(process.returncode)

    return None


if __name__ == '__main__':
    main()
