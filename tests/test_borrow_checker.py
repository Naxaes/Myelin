from borrow_checker import BorrowChecker
from ir.ir_parser import parse
import unittest


class BorrowCheckerTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_single_bb_move_ok(self):
        module = parse("""
        @test()
            $entry
                x := 32             # x is an owner
                y := move x         # Ownership of x is moved to y, x is no longer accessible
                _ := call print y   # y owns the value, so it can be read
                ret
        end
        """)
        error = BorrowChecker.check(module)
        self.assertEqual(None, error)

    def test_single_bb_move_error(self):
        module = parse("""
        @test()
            $entry
                x := 32             # x is an owner
                y := move x         # Ownership of x is moved to y, x is no longer accessible
                _ := call print x   # Error: x is no longer accessible after being moved
                ret
        end
        """)
        error = BorrowChecker.check(module)
        self.assertEqual("Error in function 'test' at block entry: Cannot use moved value 'x', it was moved to 'y'", error)

    def test_single_bb_borrow_ok(self):
        module = parse("""
        @test()
            $entry
                x := 32             # x is an owner
                y := brw x          # y borrows x immutably, x is still accessible
                _ := call print y
                ret
        end
        """)
        error = BorrowChecker.check(module)
        self.assertEqual(None, error)

    def test_single_bb_borrow_error(self):
        module = parse("""
        @test()
            $entry
                x := 32             # x is an owner
                y := brw x          # y borrows x immutably, x is still accessible
                z := move x         # Error: x is moved, so y's borrow is invalidated
                _ := call print y
                ret
        end
        """)
        error = BorrowChecker.check(module)
        self.assertEqual("Error in function 'test' at block entry: 'z' cannot move 'x'; 'x' is shared borrowed by 'y'", error)

    def test_single_bb_ref_ok(self):
        module = parse("""
        @test()
            $entry
                x := 32             # x is an owner
                y := ref x          # y borrows x immutably, x is still accessible
                _ := call print y
                ret
        end
        """)
        error = BorrowChecker.check(module)
        self.assertEqual(None, error)

    def test_single_bb_ref_error(self):
        module = parse("""
        @test()
            $entry
                x := 32             # x is an owner
                y := ref x          # y borrows x immutably, x is still accessible
                z := move x         # Error: x is moved, so y's borrow is invalidated
                _ := call print y
                ret
        end
        """)
        error = BorrowChecker.check(module)
        self.assertEqual("Error in function 'test' at block entry: 'z' cannot move 'x'; 'x' is exclusively borrowed by 'y'", error)

    def test_temporal_read_before_mutate_ok(self):
        module = parse("""
        @test()
            $entry
                x := 32
                r := ref x
                _ := call print x     # Read from owner before mutation
                r := 100              # Mutation happens after read
                ret
        end
        """)
        error = BorrowChecker.check(module)
        self.assertEqual(None, error)

    def test_conflicting_borrows_error(self):
        module = parse("""
        @test()
            $entry
                x := 32
                r1 := brw x
                r2 := ref x           # Error: cannot mutably borrow while immutably borrowed
                ret
        end
        """)
        error = BorrowChecker.check(module)
        self.assertEqual(
            "Error in function 'test' at block entry: 'r2' cannot mutably borrow 'x'; 'x' already shared borrowed by 'r1'",
            error)


if __name__ == '__main__':
    unittest.main()