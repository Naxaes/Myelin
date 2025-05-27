:i count 6
:b shell 48
python3 src/main.py examples/struct.sf     --run
:i returncode 0
:b stdout 33
Hello ted!
11
21
Exit status: 32

:b stderr 0

:b shell 48
python3 src/main.py examples/fibonacci.sf  --run
:i returncode 0
:b stdout 164


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
Exit status: 123

:b stderr 0

:b shell 48
python3 src/main.py examples/main.sf       --run
:i returncode 0
:b stdout 58
Hello world!
Hello World 0123456789
Kaboom
Exit status: 7

:b stderr 0

:b shell 48
python3 src/main.py examples/macos.sf      --run
:i returncode 0
:b stdout 15
Exit status: 0

:b stderr 0

:b shell 48
python3 src/main.py examples/core.sf       --run
:i returncode 0
:b stdout 15
Exit status: 0

:b stderr 0

:b shell 58
python3 src/main.py examples/main.ir       --check --is-ir
:i returncode 0
:b stdout 0

:b stderr 0

