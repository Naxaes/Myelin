from ir.ir_parser import parse
from ir.ir_code import c, Op
import unittest


class TestFunction(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_reaching_definitions(self):
        module = parse("""
        @test(cond: bool)
            $entry # 0
                a := 47                 # 'a0' reaches through 'left' and to 'end'.
                b := 42                 # 'b0' does not reach anywhere as this is its last use.
                br cond $left $right    # 'cond' reaches here, and it's the last use.
            $left # 1
                b := 1                  # Assignment of 'b1' doesn't affect anything since there are no uses.
                c := 5                  # 'c0' is defined here and reached 'end'.
                jmp $end
            $right # 2
                a := 2                  # 'a0' is defined and reaches 'end'.
                c := 10                 # 'c1' is defined here and reached 'end'.
                jmp $end
            $end # 3
                d := a - c              # 'a0', 'a1' and 'c0', 'c1' reaches
                print d                 # 'd' does not reach as it's defined in the block
                ret
        end
        """)
        function = module.functions['test']
        live_in, live_out = function.reaching_definitions()
        self.assertDictEqual(live_in, {
            'entry': {('a', None), ('b', None), ('c', None), ('cond', '__init__'), ('d', None)},
            'left': {('a', 'entry'), ('b', 'entry'), ('c', None), ('cond', '__init__'), ('d', None)},
            'right': {('a', 'entry'), ('b', 'entry'), ('c', None), ('cond', '__init__'), ('d', None)},
            'end': {('a', 'entry'), ('a', 'right'), ('b', 'entry'), ('b', 'left'), ('c', 'left'), ('c', 'right'),
                    ('cond', '__init__'), ('d', None)},
        })
        self.assertDictEqual(live_out, {
            'entry': {('a', 'entry'), ('b', 'entry'), ('c', None), ('cond', '__init__'), ('d', None)},
            'left': {('a', 'entry'), ('b', 'left'), ('c', 'left'), ('cond', '__init__'), ('d', None)},
            'right': {('a', 'right'), ('b', 'entry'), ('c', 'right'), ('cond', '__init__'), ('d', None)},
            'end': {('a', 'entry'), ('a', 'right'), ('b', 'entry'), ('b', 'left'), ('c', 'left'), ('c', 'right'),
                    ('cond', '__init__'), ('d', 'end')},
        })

    def test_very_busy_expressions(self):
        module = parse("""
        @test(cond: bool)
            $entry # 0
                a := 34
                b := 35
                br cond $left $right
            $left # 1
                x := b - a  # b - a is very busy since it's evaluated in all paths
                y := a - b  # a - b is noy very busy since it's not evaluated equivalent in all paths
                jmp $end
            $right # 2
                y := b - a
                a := 0
                x := a - b
                jmp $end
            $end
                print x
                print y
                ret
        end
        """)
        function = module.functions['test']
        _, busy_out = function.very_busy_expressions()
        self.assertDictEqual(busy_out, {
            'entry': {(Op.SUB, 'b', 'a')},
            'left': set(),
            'right': set(),
            'end': set(),
        })

    def test_live_variables(self):
        module = parse("""
        @test()
            $entry # 0
                x := 34
                y := 35
                cond := x > y
                br cond $left $right
            $left # 1
                one := 1
                z := x + one
                jmp $end
            $right # 2
                z := x + x
                jmp $end
            $end
                zero := 0
                x := z + zero
                print x
                ret
        end
        """)
        function = module.functions['test']
        live_in, live_out = function.live_variables()
        self.assertDictEqual(live_in, {
            'entry': set(),
            'left': {'x'},
            'right': {'x'},
            'end': {'z'},
        })
        self.assertDictEqual(live_out, {
            'entry': {'x'},
            'left': {'z'},
            'right': {'z'},
            'end': set(),
        })

    def test_interval_analysis(self):
        module = parse("""
        @test()
            $entry
                x := 0
                y := 10
                jmp $header
            $header
                cond := x < y
                br cond $body $end
            $body
                one := 1
                x := x + one
                jmp $header
            $end
                print x
                ret
        end
        """)
        function = module.functions['test']
        live_in, live_out = function.interval_analysis()
        self.assertDictEqual(live_in, {
            # No variables are entering 'entry'
            'entry': {},
            # 'cond' can only be true when entering 'header' (but might be set to false)
            'header': {'x': (0, 10), 'y': (10, 10), 'cond': (True, True), 'one': (1, 1)},
            # 'x' can only [0, 9] when 'cond' is true
            'body': {'x': (0, 9), 'y': (10, 10), 'cond': (True, True), 'one': (1, 1)},
            # 'x' can only be 10 when 'cond' is false
            'end': {'x': (10, 10), 'y': (10, 10), 'cond': (False, False), 'one': (1, 1)},
        })
        self.assertDictEqual(live_out, {
            # 'x' can only exit 'entry' with the value 0
            'entry': {'x': (0, 0), 'y': (10, 10)},
            'header': {'x': (0, 10), 'y': (10, 10), 'cond': (False, True), 'one': (1, 1)},
            'body': {'x': (1, 10), 'y': (10, 10), 'cond': (True, True), 'one': (1, 1)},
            'end': {'x': (10, 10), 'y': (10, 10), 'cond': (False, False), 'one': (1, 1)},
        })

    @unittest.skip("Don't know how to analyze free variable yet...")
    def test_interval_analysis_2(self):
        module = parse("""
        @main(x)
            $entry
                zero := 0
                y := 0
                ten := 10
                c := x < zero
                br c $end $header
            $header
                cond := x < ten
                br cond $body $end
            $body
                one := 1
                y := y + one
                x := x + one
                jmp $header
            $end
                print y
                ret
        end
        """)
        function = module.functions['test']
        live_in, live_out = function.interval_analysis()
        self.assertDictEqual(live_in, {
            'entry': {'x': (-2147483648, 2147483648)},
            'header': {'x': (0, 2147483648), 'y': (0, None), 'zero': (0, 0), 'ten': (10, 10), 'c': (False, False),
                       'cond': (True, True), 'one': (1, 1)},
            'body': {'x': (0, 9), 'y': (0, None), 'zero': (0, 0), 'ten': (10, 10), 'c': (False, False),
                     'cond': (True, True), 'one': (1, 1)},
            'end': {'x': (-2147483648, 2147483648), 'y': (0, None), 'zero': (0, 0), 'ten': (10, 10), 'c': (False, True),
                    'cond': (False, False), 'one': (1, 1)},
        })
        self.assertDictEqual(live_out, {
            'entry': {'x': (-2147483648, 2147483648), 'y': (0, 0), 'zero': (0, 0), 'ten': (10, 10), 'c': (False, True)},
            'header': {'x': (0, 2147483648), 'y': (0, None), 'zero': (0, 0), 'ten': (10, 10), 'c': (False, False),
                       'cond': (False, True), 'one': (1, 1)},
            'body': {'x': (1, 10), 'y': (1, None), 'zero': (0, 0), 'ten': (10, 10), 'c': (False, False),
                     'cond': (True, True), 'one': (1, 1)},
            'end': {'x': (-2147483648, 2147483648), 'y': (0, None), 'zero': (0, 0), 'ten': (10, 10), 'c': (False, True),
                    'cond': (False, False), 'one': (1, 1)},
        })

    def test_dominators(self):
        module = parse("""
        @test(cond: bool)
            $0
                jmp $1
            $1
                br cond $2 $4
            $2
                jmp $3
            $3
                br cond $1 $5
            $4
                jmp $5
            $5
                jmp $6
            $6
                br cond $5 $7
            $7
                ret cond
        end
        """)
        function = module.functions['test']
        dom = function.dominators()
        self.assertDictEqual(dom, {
            0: {0},
            1: {0, 1},
            2: {0, 1, 2},
            3: {0, 1, 2, 3},
            4: {0, 1, 4},
            5: {0, 1, 5},
            6: {0, 1, 5, 6},
            7: {0, 1, 5, 6, 7},
        })

    def test_borrowing_ok(self):
        module = parse("""
        @test(cond: bool)
            $entry
                one := 1
                x := 22
                y := 44
                p := ref x              # Loan L0, borrowing 'x'
                y := y + one            # (A) Mutate 'y' - Ok, no mutation of path L0
                q := ref y              # Loan L1, borrowing 'y'
                br cond $left $right
            $left                       # Loans = { L0, L1 }
                p := move q             # 'p' takes L1 - Kill of L0
                x := x + one            # (B) Mutate 'x' - Ok, no mutation of path L0
                jmp $end
            $right                      # Loans = { L1 }
                y := y + one            # (C) Mutate 'y' - Ok, no loan is active since there are no further uses of a loan from 'y'
                jmp $end
            $end                        # Loans = { L1 }
                print p                 # Use of 'p' - Ok use of L1
                ret
        end
        """)
        function = module.functions['test']
        live_in, live_out = function.live_variables()
        try:
            function.borrow_check(live_in)
        except:
            assert False

    def test_borrowing_error(self):
        module = parse("""
        @test(cond: bool)
            $entry
                one := 1
                x := 22
                y := 44
                p := ref x              # Loan L0, borrowing 'x'
                y := y + one            # (A) Mutate 'y' - Ok, no mutation of path L0
                q := ref y              # Loan L1, borrowing 'y'
                br cond $left $right
            $left
                p := move q             # 'p' takes L1 - Kill of L0
                x := x + one            # (B) Mutate 'x' - Ok, no mutation of path L0
                jmp $end
            $right
                y := y + one            # (C) Mutate 'y' - Ok, no loan is active since there are no further uses of a loan from 'y'
                jmp $end
            $end
                y := y + one            # (D) Mutate 'y' - Error, mutating path of L1 if entering '$left'
                print p                 # Use of 'p' - Ok use of L1
                ret
        end
        """)
        function = module.functions['test']
        live_in, live_out = function.live_variables()
        self.assertRaises(RuntimeError, lambda: function.borrow_check(live_in))

    def test_multiple_borrowing_error(self):
        module = parse("""
        @test(cond: bool)
            $entry
                one := 1
                x := 22
                y := 44
                p := ref x              # Loan L0, borrowing 'x'
                y := y + one            # (A) Mutate 'y' - Ok, no mutation of path L0
                q := ref y              # Loan L1, borrowing 'y'
                r := ref y              # Loan L1, borrowing 'y'
                br cond $left $right
            $left
                p := move q         # 'p' takes L1 - Kill of L0
                x := x + one        # (B) Mutate 'x' - Ok, no mutation of path L0
                jmp $end
            $right
                y := y + one        # (C) Mutate 'y' - Ok, no loan is active since there are no further uses of a loan from 'y'
                jmp $end
            $end
                y := y + one        # (D) Mutate 'y' - Error, mutating path of L1 if entering '$true'
                print r             # Use of 'p' - Ok use of L1
                ret
        end
        """)
        function = module.functions['test']
        live_in, live_out = function.live_variables()
        self.assertRaises(RuntimeError, lambda: function.borrow_check(live_in))

    def test_automatic_free(self):
        module = parse("""
        @test()
            $entry
                c := 32
                a := alloc c
                i := 0
                one := 1
                jmp $loop
            $loop
                two := 2
                val := i * two
                set a i val
                i := i + one
                cond := i < c
                br cond $loop $end
            $end
                x := 30
                y := a + x
                print a
                print y
                ret
        end
        """)
        function = module.functions['test']
        function.automatically_drop()
        assert function.blocks[-1].instructions[-1].op == Op.FREE, f"Last instruction should be a free operation, but got {function.blocks[-1].instructions[-2]}"

    @unittest.skip("Need to fix explicit free")
    def test_automatic_free_2(self):
        """An allocated value should be dropped at every execution path"""
        module = parse("""
        @main(cond)
            count := 32
            array := alloc count
            br cond $true $false

            $true
                jmp $end
            $false
                free array
                jmp $end
            $end
                print count
        end
        """)
        function = module.functions['test']
        function.automatically_drop()
        assert function.block_at('true').instructions[-2]['op'] == Op.FREE
        assert function.block_at('false').instructions[-2]['op'] == Op.FREE

    def test_static_slice(self):
        module = parse("""
        @test(n: int)
            $entry
                sum := 0
                product := 1
                w := 7
                jmp $header
            $header
                i := 1
                cond := i < n
                br cond $body $end
            $body
                temp := i + w
                sum := sum + temp
                product := product * i
                jmp $header
            $end
                print sum
                print product
                ret
        end
        """)
        function = module.functions['test']
        slice = function.static_slice('sum')
        self.assertDictEqual(slice, {
            'entry': [
                c(op=Op.LIT, dest='sum', args=('int', 0, 0)),
                c(op=Op.LIT, dest='w', args=('int', 2, 7)),
            ],
            'header': [
                c(op=Op.LIT, dest='i', args=('int', 3, 1)),
                c(op=Op.LT, dest='cond', refs=('i', 'n')),
            ],
            'body': [
                c(op=Op.ADD, dest='temp', refs=('i', 'w')),
                c(op=Op.ADD, dest='sum', refs=('sum', 'temp')),
            ],
            'end': [
                c(op=Op.PRINT, refs=('sum',)),
            ],
        })


if __name__ == '__main__':
    unittest.main()

    """
    https://en.wikipedia.org/wiki/Interval_arithmetic
    a < b

    if max(a) <  min(b) =>  a, b  |  -, -   (always true)
    if min(a) >= max(b) =>  -, -  |  a, b   (always false)


    lhs = () - a0, a1
    rhs = [] - b0, b1
    operator = <

    a < b is True:
        ()[] - a = a, b = b
        ([)] - a = (a0, a1), b = (b0, b1)
        ([]) - a = (a0, b1), b = (b0, b1)
        [()] - a = (a0, a1), b = (a0, b1)
        [(]) - a = (a0, b1), b = (a0, b1)
        []() - a = None, b = None

    a = (a0, min(a1, b1))
    b = (max(a0, b0), b1)


    a < b is False:
        ()[] - a = None, b = None
        ([)] - a = (b0, a1), b = (b0, b1)
        ([]) - a = (b0, a1), b = (b0, b1)
        [()] - a = (a0, a1), b = (a0, b1)
        [(]) - a = (a0, a1), b = (a0, b1)
        []() - a = a, b = b

    """






