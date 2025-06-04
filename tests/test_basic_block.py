from ir.ir_code import c, Op
from ir.basic_block import Block

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

if __name__ == '__main__':
    unittest.main()
