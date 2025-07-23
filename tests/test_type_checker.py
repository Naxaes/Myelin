from ir.ir_parser import parse
from type_checker import TypeChecker
from type import *
import unittest

class TypeCheckerTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_types(self):
        module = parse("""
        @test_0()
            $entry
                n := 32
                x := call alloc n
                y := move x
                _ := call print y
                ret
        end
        """)
        function = module.functions['test_0']
        types = TypeChecker.check(module)
        self.assertEqual({
            None: PrimitiveType(name='void', size=0),
            'n': LiteralType(value=32),
            'x': PointerType(PrimitiveType(name='void', size=0)),
            'y': PointerType(PrimitiveType(name='void', size=0)),
            '_': PrimitiveType(name='int', size=8),
        }, types[function.name])

if __name__ == '__main__':
    unittest.main()