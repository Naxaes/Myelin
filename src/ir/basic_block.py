from typing import Optional, Any
from collections import namedtuple

from ir import Op, Code, INSTRUCTIONS, SIDE_EFFECTS, TERMINATORS

Entry = namedtuple('Entry', ('value', 'variable'))

def find(table, v):
    for i, entry in table.items():
        if entry.value == v:
            return i
    return None


class Block:
    def __init__(self, label: str, instructions: list[Code] = (), terminator: Optional[Code] = None, parameters: tuple[dict] = ()):
        assert all(x.op in INSTRUCTIONS for x in instructions)

        self.label        = label
        self.instructions = list(instructions)
        self.terminator   = terminator
        self.parameters   = parameters
        assert self.terminator.op in TERMINATORS if instructions else True, f"Invalid terminator '{self.terminator.op}' in block {self.label}, expected one of {TERMINATORS}"

    def add(self, instruction: Code) -> int:
        assert instruction.op in INSTRUCTIONS, f"Invalid instruction '{instruction.op}' in block {self.label}, expected one of {INSTRUCTIONS}"
        id = len(self.instructions)
        self.instructions.append(instruction)
        return id

    def gen(self) -> set[str]:
        """
        The set of all variables defined to in this basic block.
        Example:
            a := x + y      # 'a' is defined
            b := a + z      # 'b' is defined
            c := b + a      # 'c' is defined
            ----
            { 'a', 'b', 'c' }
        """
        return { i.dest for i in self.instructions if i.dest is not None }

    def use(self) -> set[str]:
        """
        The set of all variables read from, unless overridden, in this basic block.
        I.e. uses of in-variables.
        Example:
            a := x + y      # 'x', 'y' is used
            b := a + z      # 'z' is used, 'a' is not used as it's defined in this block
            c := b + a      # 'a' and 'b' is not used as they're defined in this block
            ----
            { 'x', 'y', 'z' }
        """
        defined = set()
        used: set[str] = set()
        for i in self.instructions:
            used.update(v for v in i.refs if v not in defined)
            if i.dest:
                defined.add(i.dest)
        return used

    def canonicalize(self) -> None:
        """
        1. Order arguments for commutative instructions in alphabetical order.
        """
        for instruction in self.instructions:
            if instruction.refs and instruction.op in (Op.ADD, Op.MUL, Op.EQ, Op.NEQ):
                instruction.refs = tuple(sorted(instruction.refs))

    def to_ssa(self) -> None:
        def rename(x):
            if "'" in x:
                name, version = x.split("'")
                version = str(int(version) + 1)
                return name + "'" + version
            else:
                return x + "'0"

        defined = set()
        for i, instruction in enumerate(self.instructions):
            if old_name := instruction.dest:
                if old_name in defined:
                    new_name = rename(old_name)
                    for candidate in self.instructions[i+1:]:
                        if candidate.refs:
                            candidate.refs = tuple(new_name if x == old_name else x for x in candidate.refs)
                        if candidate.dest and candidate.dest == old_name:
                            candidate.dest = new_name
                    defined.add(new_name)
                    instruction.dest = new_name
                else:
                    defined.add(old_name)


    def remove_nop(self):
        self.instructions = [i for i in self.instructions if i.op != Op.NOP]

    def lvn(self, table: dict[int, Entry], environment: dict[str, int]) -> tuple[dict[int, Entry], dict[str, int]]:
        table = table.copy()
        environment = environment.copy()
        value: tuple[Op, Any, Any]

        for instruction in self.instructions:
            if instruction.dest:
                name = instruction.dest
                if instruction.op == Op.LIT:
                    ty, idx, val = instruction.args
                    value = (instruction.op, val, None)
                    if (identical := find(table, value)) is not None:
                        # If we found an identical value, we'll use that value instead of this, so we can delete it.
                        instruction.op = Op.NOP
                        environment[name] = identical
                    else:
                        environment[name] = len(table)
                        table[len(table)] = Entry(value, name)
                elif instruction.op in (Op.REF, Op.MOVE, Op.ALLOC):
                    value = (instruction.op, environment[instruction.refs[0]], None)
                    instruction.refs  = (table[value[1]].variable,)
                    environment[name] = len(table)
                    table[len(table)] = Entry(value, name)
                else:
                    value = (instruction.op, environment[instruction.refs[0]], environment[instruction.refs[1]])
                    if (identical := find(table, value)) is not None:
                        # If we found an identical value, we'll use that value instead of this, so we can delete it.
                        instruction.op = Op.NOP
                        environment[name] = identical
                    else:
                        instruction.refs = (table[value[1]].variable, table[value[2]].variable)
                        environment[name] = len(table)
                        table[len(table)] = Entry(value, name)
            elif instruction.refs:
                instruction.refs = tuple(table[environment[arg]].variable for arg in instruction.refs)

        self.remove_nop()

        return table, environment

    def dce(self, keep: Optional[set[str]] = None):
        """
        Removes all unused code.
        :param keep: Variables used after this basic block, i.e. variables not to be removed.
        """
        used: set[str] = (keep and keep.copy()) or set()
        for i in reversed(self.instructions):
            if i.op in SIDE_EFFECTS:
                # All instructions with side effects must be kept
                used.update(i.refs)
            elif i.dest and i.dest not in used or i.op == Op.NOP:
                # Instructions that haven't been used can be removed
                self.instructions.remove(i)
            elif i.refs:
                used.update(i.refs)

    def borrow_check(self, loans: dict[str, set[str]], live_variables: set[str]) -> dict[str, set[str]]:
        """

        :param loans: A mapping from a variable being loaned to the loaners.
        :param live_variables: A set of variables whose definition is active in the block.
        :return: A dictionary of the current active loans out of this block
        """
        loaned_variables = {a: b.intersection(live_variables) for a, b in loans.items()}
        loaned_variables = { a: b for a, b in loaned_variables.items() if b }
        for instruction in self.instructions:
            if (name := instruction.dest or '') in loaned_variables:
                loaned_by = loaned_variables[name]
                raise RuntimeError(f'Modifying variable {name} while loaned by {loaned_by}')

            if instruction.op == Op.REF:
                arg = instruction.refs[0]
                if arg in loaned_variables:
                    loaned_variables[arg].add(instruction.dest)
                else:
                    loaned_variables[arg] = {instruction.dest}
            elif instruction.op == Op.MOVE:
                arg = instruction.refs[0]
                name = instruction.dest
                for key, values in list(loaned_variables.items()):
                    if arg in values:
                        if arg in loaned_variables:
                            loaned_variables[arg].add(name)
                        else:
                            for a, b in list(loaned_variables.items()):
                                if arg in b:
                                    b.remove(arg)
                                    b.add(name)
                                else:
                                    assert False
                            # loaned_variables[arg] = {name}
                    # if name in values:
                    #     loaned_variables[key].remove(name)
                    #     if not loaned_variables[key]:
                    #         print(f'Loan of {key} by {name} was removed')
                    #         del loaned_variables[key]

        return loaned_variables

    def check_drops(self, dropees: set[str]):
        for instruction in self.instructions:
            if instruction.op == Op.ALLOC:
                dropees.add(instruction.dest)
            elif instruction.op == Op.FREE:
                arg = instruction.refs[0]
                if arg in dropees:
                    dropees.remove(arg)

    def __repr__(self):
        uses = ', '.join(x for x in self.use() if type(x) == str)
        return f"Block(label='{self.label}', arguments=({uses}))"
