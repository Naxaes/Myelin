:i count 5
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

