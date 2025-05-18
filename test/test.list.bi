:i count 6
:b shell 60
python3 src/main.py examples/struct.sf     && ./build/struct
:i returncode 32
:b stdout 17
Hello ted!
11
21

:b stderr 0

:b shell 63
python3 src/main.py examples/fibonacci.sf  && ./build/fibonacci
:i returncode 123
:b stdout 147


1
1
2
1
3
2
4
3
5
5
6
8
7
13
8
21
9
34
10
55
11
89
12
144
13
233
14
377
15
610
16
987
17
1597
18
2584
19
4181
20
6765
21
10946
22
17711
23
28657

:b stderr 0

:b shell 58
python3 src/main.py examples/main.sf       && ./build/main
:i returncode 7
:b stdout 43
Hello world!
Hello World 0123456789
Kaboom

:b stderr 0

:b shell 59
python3 src/main.py examples/macos.sf      && ./build/macos
:i returncode 0
:b stdout 0

:b stderr 0

:b shell 58
python3 src/main.py examples/core.sf       && ./build/core
:i returncode 0
:b stdout 0

:b stderr 0

:b shell 60
python3 -m unittest src/ir/basic_block.py src/ir/function.py
:i returncode 1
:b stdout 0

:b stderr 1463
EE
======================================================================
ERROR: basic_block (unittest.loader._FailedTest.basic_block)
----------------------------------------------------------------------
ImportError: Failed to import test module: basic_block
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/unittest/loader.py", line 137, in loadTestsFromName
    module = __import__(module_name)
             ^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/klein002/Programming/Myelin/src/ir/basic_block.py", line 4, in <module>
    from ir.ir import INSTRUCTIONS, SIDE_EFFECTS, TERMINATORS, Code
ModuleNotFoundError: No module named 'ir'


======================================================================
ERROR: function (unittest.loader._FailedTest.function)
----------------------------------------------------------------------
ImportError: Failed to import test module: function
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/unittest/loader.py", line 137, in loadTestsFromName
    module = __import__(module_name)
             ^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/klein002/Programming/Myelin/src/ir/function.py", line 3, in <module>
    from ir.basic_block import Block, Entry
ModuleNotFoundError: No module named 'ir'


----------------------------------------------------------------------
Ran 2 tests in 0.000s

FAILED (errors=2)

