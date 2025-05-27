from typing import Optional, Any
from collections import namedtuple

from ir.ir import Op, Code, INSTRUCTIONS, SIDE_EFFECTS, TERMINATORS

Entry = namedtuple('Entry', ('value', 'variable'))

def find(table, v):
    for i, entry in table.items():
        if entry.value == v:
            return i


class Block:
    def __init__(self, label: str, instructions: list[Code] = (), terminator: Optional[Code] = None, parameters: tuple[dict] = ()):
        assert all(x.op in INSTRUCTIONS for x in instructions)

        self.label        = label
        self.instructions = list(instructions)
        self.terminator   = terminator
        self.parameters   = parameters
        assert self.terminator.op in TERMINATORS if instructions else True, f"Invalid terminator '{self.terminator.op}' in block {self.label}, expected one of {TERMINATORS}"

    def add(self, instruction: Code) -> None:
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
                        print(f'Found duplicate value for {name}')
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
        print(f'[START] Block: {self.label} | loans: {loaned_variables} | reaching: {live_variables}')
        for instruction in self.instructions:
            if (name := instruction.dest or '') in loaned_variables:
                loaned_by = loaned_variables[name]
                print(f'Modifying variable {name} while loaned by {loaned_by}')
                raise RuntimeError(f'Modifying variable {name} while loaned by {loaned_by}')

            if instruction.op == Op.REF:
                arg = instruction.refs[0]
                if arg in loaned_variables:
                    loaned_variables[arg].add(instruction.dest)
                    print(f'{arg} was loaned by {instruction.dest} also: loans = {loaned_variables}')
                else:
                    loaned_variables[arg] = {instruction.dest}
                    print(f'{arg} was loaned by {instruction.dest}: loans = {loaned_variables}')
            elif instruction.op == Op.MOVE:
                arg = instruction.refs[0]
                name = instruction.dest
                for key, values in list(loaned_variables.items()):
                    if arg in values:
                        if arg in loaned_variables:
                            loaned_variables[arg].add(name)
                            print(f'{arg} was taken by {name} also: loans = {loaned_variables}')
                        else:
                            for a, b in list(loaned_variables.items()):
                                if arg in b:
                                    b.remove(arg)
                                    b.add(name)
                                else:
                                    assert False
                            # loaned_variables[arg] = {name}
                            print(f'{arg} was taken by {name}: loans = {loaned_variables}')
                    # if name in values:
                    #     loaned_variables[key].remove(name)
                    #     if not loaned_variables[key]:
                    #         print(f'Loan of {key} by {name} was removed')
                    #         del loaned_variables[key]

        print(f'[STOP] Block: {self.label} | loans: {loaned_variables} | reaching: {live_variables}')
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



from ir.ir import c

import unittest

class TestBasicBlock(unittest.TestCase):

    def test_use(self):
        """
        a := x + y      # 'x', 'y' is used
        b := a + z      # 'z' is used, 'a' is not used as it's defined in this block
        c := b + a      # 'a' and 'b' is not used as they're defined in this block
        ----
        { 'x', 'y', 'z' }
        """
        instructions = [
            c(op=Op.ADD, dest="a", refs=("x", "y")),
            c(op=Op.ADD, dest="b", refs=("a", "z")),
            c(op=Op.ADD, dest="c", refs=("a", "b")),
        ]
        block = Block('test', instructions, terminator=c(op=Op.RET))
        used = block.use()
        self.assertEqual(used, {'x', 'y', 'z'})

    def test_dce_remove_dead_code(self):
        instructions = [
            c(op=Op.LIT, dest="a", args=('int', 0, 4)),
            c(op=Op.LIT, dest="b", args=('int', 1, 2)),
            c(op=Op.LIT, dest="c", args=('int', 2, 1)),
            c(op=Op.ADD, dest="d", refs=("a", "b")),
            c(op=Op.ADD, dest="e", refs=("c", "d")),
            c(op=Op.PRINT, refs=("d", )),
        ]
        block = Block('test', instructions, terminator=c(op=Op.RET))
        block.dce()
        self.assertEqual(block.instructions, [
            c(op=Op.LIT, dest="a", args=('int', 0, 4)),
            c(op=Op.LIT, dest="b", args=('int', 1, 2)),
            c(op=Op.ADD, dest="d", refs=("a", "b")),
            c(op=Op.PRINT, refs=("d", )),
        ])

    def test_dce_dont_remove_reuse_of_variable(self):
        instructions = [
            c(op=Op.LIT, dest="a", args=('int', 0, 1)),
            c(op=Op.LIT, dest="b", args=('int', 1, 2)),
            c(op=Op.ADD, dest="c", refs=("a", "b")),
            c(op=Op.LIT, dest="a", args=('int', 2, 3)),
            c(op=Op.ADD, dest="d", refs=("a", "c")),
            c(op=Op.PRINT, refs=("d", )),
        ]
        block = Block('test', instructions, terminator=c(op=Op.RET))
        block.dce()
        self.assertEqual(block.instructions, [
            c(op=Op.LIT, dest="a", args=('int', 0, 1)),
            c(op=Op.LIT, dest="b", args=('int', 1, 2)),
            c(op=Op.ADD, dest="c", refs=("a", "b")),
            c(op=Op.LIT, dest="a", args=('int', 2, 3)),
            c(op=Op.ADD, dest="d", refs=("a", "c")),
            c(op=Op.PRINT, refs=("d", )),
        ])

    def test_dce_with_args(self):
        instructions = [
            c(op=Op.LIT, dest="a", args=('int', 0, 4)),
            c(op=Op.LIT, dest="b", args=('int', 1, 2)),
            c(op=Op.LIT, dest="c", args=('int', 2, 1)),
            c(op=Op.ADD, dest="d", refs=("a", "b")),
            c(op=Op.ADD, dest="e", refs=("c", "d")),
            c(op=Op.LIT, dest="f", args=('int', 4, 1)),
            c(op=Op.PRINT, refs=("d", )),
        ]
        block = Block('test', instructions, terminator=c(op=Op.RET))
        block.dce(keep={"c", "f"})
        self.assertEqual(block.instructions, [
            c(op=Op.LIT, dest="a", args=('int', 0, 4)),
            c(op=Op.LIT, dest="b", args=('int', 1, 2)),
            c(op=Op.LIT, dest="c", args=('int', 2, 1)),
            c(op=Op.ADD, dest="d", refs=("a", "b")),
            c(op=Op.LIT, dest="f", args=('int', 4, 1)),
            c(op=Op.PRINT, refs=("d", )),
        ])

    def test_lvn_remove_duplicate_values(self):
        instructions = [
            c(op=Op.LIT, dest="a", args=('int', 0, 4)),
            c(op=Op.LIT, dest="b", args=('int', 1, 4)),
            c(op=Op.ADD, dest="sum1", refs=("a", "b")),
            c(op=Op.ADD, dest="sum2", refs=("a", "b")),
            c(op=Op.MUL, dest="prod", refs=("sum1", "sum2")),
            c(op=Op.MUL, dest="x", refs=("sum1", "sum2")),
            c(op=Op.PRINT, refs=("x", )),
        ]
        block = Block('test', instructions, terminator=c(op=Op.RET))
        block.lvn({}, {})
        self.assertEqual(block.instructions, [
            c(op=Op.LIT, dest="a", args=('int', 0, 4)),
            c(op=Op.ADD, dest="sum1", refs=("a", "a")),
            c(op=Op.MUL, dest="prod", refs=("sum1", "sum1")),
            c(op=Op.PRINT, refs=("prod", )),
        ])

    def test_lvn_with_overwritten_variable(self):
        instructions = [
            c(op=Op.LIT, dest="a", args=('int', 0, 1)),
            c(op=Op.LIT, dest="b", args=('int', 1, 1)),
            c(op=Op.ADD, dest="x", refs=("a", "b")),   # Should replace b with a
            c(op=Op.PRINT, refs=("x", )),
            c(op=Op.LIT, dest="x", args=('int', 2, 3)),          # Should be renamed to x'
            c(op=Op.ADD, dest="y", refs=("a", "b")),   # Should be replaced by x
            c(op=Op.ADD, dest="z", refs=("x", "y")),   # Should replace x to x' and y to x
            c(op=Op.PRINT, refs=("z", )),
        ]
        block = Block('test', instructions, terminator=c(op=Op.RET))
        block.to_ssa()
        block.lvn({}, {})
        self.assertEqual(block.instructions, [
            c(op=Op.LIT, dest="a", args=('int', 0, 1)),
            c(op=Op.ADD, dest="x", refs=("a", "a")),
            c(op=Op.PRINT, refs=("x", )),
            c(op=Op.LIT, dest="x'0", args=('int', 2, 3)),
            c(op=Op.ADD, dest="z", refs=("x'0", "x")),
            c(op=Op.PRINT, refs=("z", )),
        ])

    def test_lvn_with_overwritten_variable_multiple_times(self):
        instructions = [
            c(op=Op.LIT, dest="a", args=('int', 0, 1)),
            c(op=Op.LIT, dest="a", args=('int', 1, 1)),   # Should be removed
            c(op=Op.ADD, dest="a", refs=("a", "a")),      # Should be renamed to a''
            c(op=Op.PRINT, refs=("a", )),                 # Should be replaced by a''
            c(op=Op.LIT, dest="a", args=('int', 2, 3)),   # Should be renamed to a'''
            c(op=Op.ADD, dest="a", refs=("a", "a")),      # Should be replaced by a''' and a''' and renamed to a''''
            c(op=Op.PRINT, refs=("a", )),                 # Should be replaced by a''''
        ]
        block = Block('test', instructions, terminator=c(op=Op.RET))
        block.to_ssa()
        block.lvn({}, {})
        print(*block.instructions, sep='\n')
        self.assertEqual(block.instructions, [
            c(op=Op.LIT, dest="a", args=('int', 0, 1)),
            c(op=Op.ADD, dest="a'1", refs=("a", "a")),
            c(op=Op.PRINT, refs=("a'1", )),
            c(op=Op.LIT, dest="a'2", args=('int', 2, 3)),
            c(op=Op.ADD, dest="a'3", refs=("a'2", "a'2")),
            c(op=Op.PRINT, refs=("a'3", )),
        ])

    def test_borrowing(self):
        """
        a := malloc 22
        b := ref a      # 'a' is immutably borrowed
        print b         # Ok
        a += 1          # 'a' is mutated, but 'b' is not borrowed
        """
        instructions = [
            c(op=Op.LIT, dest="one", args=('int', 0, 1)),
            c(op=Op.LIT, dest="x", args=('int', 1, 22)),
            c(op=Op.LIT, dest="y", args=('int', 2, 44)),
            c(op=Op.REF, dest="p", refs=("x", )),
            c(op=Op.ADD, dest="y", refs=("y", "one")),
            c(op=Op.REF, dest="q", refs=("y", )),
        ]
        block = Block('test', instructions, terminator=c(op=Op.RET))
        loans = block.borrow_check({}, set())
        print(loans)

if __name__ == '__main__':
    unittest.main()
