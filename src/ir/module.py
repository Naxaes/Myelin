from typing import Dict, Union

from ir.function import Function, Builtin


class Module:
    def __init__(self, name: str, functions: Dict[str, Union[Function, Builtin]], data: Dict, constants: Dict, types: Dict, imports: Dict):
        self.name = name
        self.functions = functions
        # Static data needed in the executable
        self.data = data
        # Constants inlined in the code
        self.constants = constants
        self.types = types
        self.imports = imports

    def __repr__(self):
        result = f"Module: {self.name}\n"
        for name, func in self.functions.items():
            result += f"  Function: {name}\n"
            for block in func.blocks:
                result += f"    Block: {block.label}\n"
                for instruction in block.instructions:
                    result += f"      {instruction}\n"
                result += f"      {block.terminator}\n"
        return result