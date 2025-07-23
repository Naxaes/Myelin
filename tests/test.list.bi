:i count 14
:b shell 63
PYTHONPATH=src python3 src/main.py examples/struct.sf     --run
:i returncode 32
:b stdout 17
Hello ted!
11
21

:b stderr 0

:b shell 63
PYTHONPATH=src python3 src/main.py examples/fibonacci.sf  --run
:i returncode 123
:b stdout 149
0
0
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

:b shell 63
PYTHONPATH=src python3 src/main.py examples/main.sf       --run
:i returncode 7
:b stdout 43
Hello world!
Hello World 0123456789
Kaboom

:b stderr 0

:b shell 63
PYTHONPATH=src python3 src/main.py examples/macos.sf      --run
:i returncode 0
:b stdout 0

:b stderr 0

:b shell 63
PYTHONPATH=src python3 src/main.py examples/core.sf       --run
:i returncode 0
:b stdout 0

:b stderr 0

:b shell 0

:i returncode 0
:b stdout 0

:b stderr 0

:b shell 73
PYTHONPATH=src python3 src/main.py examples/main.ir       --check --is-ir
:i returncode 0
:b stdout 0

:b stderr 0

:b shell 68
PYTHONPATH=src python3 -m unittest discover tests -q -b 2> /dev/null
:i returncode 0
:b stdout 0

:b stderr 0

:b shell 0

:i returncode 0
:b stdout 0

:b stderr 0

:b shell 20
cat build/struct.dot
:i returncode 0
:b stdout 9925
// Control Flow Graph
digraph {
	subgraph cluster_alloc {
		label=alloc
	}
	"struct.sf__bb0_entry" -> display_foo__bb0_entry [style=dotted]
	"struct.sf__bb0_entry" -> print_int__bb0_entry [style=dotted]
	"struct.sf__bb0_entry" -> exit__bb0_entry [style=dotted]
	subgraph "cluster_struct.sf" {
		label="struct.sf"
		"struct.sf__bb0_entry" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v0 : int = 11</TD></TR><TR><TD ALIGN="LEFT">01│ v1 :: .bar = %0</TD></TR><TR><TD ALIGN="LEFT">02│ v2 : str = Hello ted!\n</TD></TR><TR><TD ALIGN="LEFT">03│ v3 :: .baz = %2</TD></TR><TR><TD ALIGN="LEFT">04│ v4 := Foo{%1, %3}</TD></TR><TR><TD ALIGN="LEFT">05│ foo := %4</TD></TR><TR><TD ALIGN="LEFT">06│ v5 = display_foo(%foo)</TD></TR><TR><TD ALIGN="LEFT">07│ x, y := %6</TD></TR><TR><TD ALIGN="LEFT">08│ v7 = print_int(%x)</TD></TR><TR><TD ALIGN="LEFT">09│ v8 = print_int(%y)</TD></TR><TR><TD ALIGN="LEFT">10│ v9 := %x + %y</TD></TR><TR><TD ALIGN="LEFT">11│ v10 = exit(%10)</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret </TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	subgraph cluster_write {
		label=write
		write__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ fd: int</TD></TR><TR><TD ALIGN="LEFT">01│ buffer: ptr</TD></TR><TR><TD ALIGN="LEFT">02│ count: int</TD></TR><TR><TD ALIGN="LEFT">03│ syscall %SYS_WRITE</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %3</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	subgraph cluster_exit {
		label=exit
		exit__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ code: int</TD></TR><TR><TD ALIGN="LEFT">01│ syscall %SYS_EXIT</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %1</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	print__bb0_entry -> write__bb0_entry [style=dotted]
	subgraph cluster_print {
		label=print
		print__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ message: str</TD></TR><TR><TD ALIGN="LEFT">01│ size: int</TD></TR><TR><TD ALIGN="LEFT">02│ v1 := %message as ptr</TD></TR><TR><TD ALIGN="LEFT">03│ v2 = write(%STDOUT, %2, %size)</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %3</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	print_int__bb0_entry -> alloc [style=dotted]
	print_int__bb4_while_end -> write__bb0_entry [style=dotted]
	subgraph cluster_print_int {
		label=print_int
		print_int__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ n: int</TD></TR><TR><TD ALIGN="LEFT">01│ v1 : int = 21</TD></TR><TR><TD ALIGN="LEFT">02│ count := %1</TD></TR><TR><TD ALIGN="LEFT">03│ v2 = alloc(%count)</TD></TR><TR><TD ALIGN="LEFT">04│ v3 := %3 as str</TD></TR><TR><TD ALIGN="LEFT">05│ buffer := %4</TD></TR><TR><TD ALIGN="LEFT">06│ v4 : int = 1</TD></TR><TR><TD ALIGN="LEFT">07│ v5 := %count - %6</TD></TR><TR><TD ALIGN="LEFT">08│ i := %7</TD></TR><TR><TD ALIGN="LEFT">09│ v6 := %buffer[%i]</TD></TR><TR><TD ALIGN="LEFT">10│ v7 : int = 10</TD></TR><TR><TD ALIGN="LEFT">11│ %9 = %10</TD></TR><TR><TD ALIGN="LEFT">12│ v8 : int = 1</TD></TR><TR><TD ALIGN="LEFT">13│ v9 := %i - %12</TD></TR><TR><TD ALIGN="LEFT">14│ %i = %13</TD></TR><TR><TD ALIGN="LEFT">15│ v10 : int = 0</TD></TR><TR><TD ALIGN="LEFT">16│ v11 := %n == %15</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">if %16 then $1 else $2</TD></TR>
                    </TABLE>
                > shape=plaintext]
		print_int__bb0_entry -> print_int__bb1_if_then
		print_int__bb0_entry -> print_int__bb3_while
		print_int__bb1_if_then [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb1_if_then</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v12 := %buffer[%i]</TD></TR><TR><TD ALIGN="LEFT">01│ v13 : int = 48</TD></TR><TR><TD ALIGN="LEFT">02│ %0 = %1</TD></TR><TR><TD ALIGN="LEFT">03│ v14 : int = 1</TD></TR><TR><TD ALIGN="LEFT">04│ v15 := %i - %3</TD></TR><TR><TD ALIGN="LEFT">05│ %i = %4</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $2</TD></TR>
                    </TABLE>
                > shape=plaintext]
		print_int__bb1_if_then -> print_int__bb3_while
		print_int__bb3_while [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb3_while</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v16 : int = 0</TD></TR><TR><TD ALIGN="LEFT">01│ v17 := %n != %0</TD></TR><TR><TD ALIGN="LEFT">02│ v18 : int = 0</TD></TR><TR><TD ALIGN="LEFT">03│ v19 := %i != %2</TD></TR><TR><TD ALIGN="LEFT">04│ v20 := %1 and %3</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">if %4 then $3 else $4</TD></TR>
                    </TABLE>
                > shape=plaintext]
		print_int__bb3_while -> print_int__bb3_while_then
		print_int__bb3_while -> print_int__bb4_while_end
		print_int__bb3_while_then [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb3_while_then</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v21 := %buffer[%i]</TD></TR><TR><TD ALIGN="LEFT">01│ v22 : int = 48</TD></TR><TR><TD ALIGN="LEFT">02│ v23 : int = 10</TD></TR><TR><TD ALIGN="LEFT">03│ v24 := %n % %2</TD></TR><TR><TD ALIGN="LEFT">04│ v25 := %1 + %3</TD></TR><TR><TD ALIGN="LEFT">05│ %0 = %4</TD></TR><TR><TD ALIGN="LEFT">06│ v26 : int = 10</TD></TR><TR><TD ALIGN="LEFT">07│ v27 := %n / %6</TD></TR><TR><TD ALIGN="LEFT">08│ %n = %7</TD></TR><TR><TD ALIGN="LEFT">09│ v28 : int = 1</TD></TR><TR><TD ALIGN="LEFT">10│ v29 := %i - %9</TD></TR><TR><TD ALIGN="LEFT">11│ %i = %10</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $2</TD></TR>
                    </TABLE>
                > shape=plaintext]
		print_int__bb3_while_then -> print_int__bb3_while
		print_int__bb4_while_end [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb4_while_end</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v30 := %buffer + %i</TD></TR><TR><TD ALIGN="LEFT">01│ v31 : int = 1</TD></TR><TR><TD ALIGN="LEFT">02│ v32 := %0 + %1</TD></TR><TR><TD ALIGN="LEFT">03│ v33 : int = 1</TD></TR><TR><TD ALIGN="LEFT">04│ v34 := %count - %3</TD></TR><TR><TD ALIGN="LEFT">05│ v35 := %4 - %i</TD></TR><TR><TD ALIGN="LEFT">06│ v36 = write(%STDOUT, %2, %5)</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %6</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	display_foo__bb0_entry -> temp__bb0_entry [style=dotted]
	subgraph cluster_display_foo {
		label=display_foo
		display_foo__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ obj: Foo</TD></TR><TR><TD ALIGN="LEFT">01│ v1 := %obj.%bar</TD></TR><TR><TD ALIGN="LEFT">02│ v2 = temp(%obj)</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %1, %2</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	temp__bb0_entry -> print__bb0_entry [style=dotted]
	subgraph cluster_temp {
		label=temp
		temp__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ thing: Foo</TD></TR><TR><TD ALIGN="LEFT">01│ v1 := %thing.%baz</TD></TR><TR><TD ALIGN="LEFT">02│ v2 := %thing.%bar</TD></TR><TR><TD ALIGN="LEFT">03│ v3 = print(%1, %2)</TD></TR><TR><TD ALIGN="LEFT">04│ v4 := %thing.%bar</TD></TR><TR><TD ALIGN="LEFT">05│ v5 : int = 10</TD></TR><TR><TD ALIGN="LEFT">06│ v6 := %4 + %5</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %6</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
}

:b stderr 0

:b shell 23
cat build/fibonacci.dot
:i returncode 0
:b stdout 8700
// Control Flow Graph
digraph {
	subgraph cluster_alloc {
		label=alloc
	}
	"fibonacci.sf__bb2_while_then" -> print_int__bb0_entry [style=dotted]
	subgraph "cluster_fibonacci.sf" {
		label="fibonacci.sf"
		"fibonacci.sf__bb0_entry" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v0 : int = 0</TD></TR><TR><TD ALIGN="LEFT">01│ a := %0</TD></TR><TR><TD ALIGN="LEFT">02│ v1 : int = 1</TD></TR><TR><TD ALIGN="LEFT">03│ b := %2</TD></TR><TR><TD ALIGN="LEFT">04│ v2 : int = 0</TD></TR><TR><TD ALIGN="LEFT">05│ i := %4</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $1</TD></TR>
                    </TABLE>
                > shape=plaintext]
		"fibonacci.sf__bb0_entry" -> "fibonacci.sf__bb1_while"
		"fibonacci.sf__bb1_while" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb1_while</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v3 : int = 100</TD></TR><TR><TD ALIGN="LEFT">01│ v4 := %i &lt; %0</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">if %1 then $2 else $3</TD></TR>
                    </TABLE>
                > shape=plaintext]
		"fibonacci.sf__bb1_while" -> "fibonacci.sf__bb2_while_then"
		"fibonacci.sf__bb1_while" -> "fibonacci.sf__bb3_while_end"
		"fibonacci.sf__bb2_while_then" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb2_while_then</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v5 = print_int(%i)</TD></TR><TR><TD ALIGN="LEFT">01│ v6 = print_int(%a)</TD></TR><TR><TD ALIGN="LEFT">02│ v7 := %a + %b</TD></TR><TR><TD ALIGN="LEFT">03│ c := %2</TD></TR><TR><TD ALIGN="LEFT">04│ %a = %b</TD></TR><TR><TD ALIGN="LEFT">05│ %b = %c</TD></TR><TR><TD ALIGN="LEFT">06│ v8 : int = 1</TD></TR><TR><TD ALIGN="LEFT">07│ v9 := %i + %6</TD></TR><TR><TD ALIGN="LEFT">08│ %i = %7</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $1</TD></TR>
                    </TABLE>
                > shape=plaintext]
		"fibonacci.sf__bb2_while_then" -> "fibonacci.sf__bb1_while"
		"fibonacci.sf__bb3_while_end" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb3_while_end</B></TD></TR>
                        
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret </TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	subgraph cluster_write {
		label=write
		write__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ fd: int</TD></TR><TR><TD ALIGN="LEFT">01│ buffer: ptr</TD></TR><TR><TD ALIGN="LEFT">02│ count: int</TD></TR><TR><TD ALIGN="LEFT">03│ syscall %SYS_WRITE</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %3</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	print_int__bb0_entry -> alloc [style=dotted]
	print_int__bb4_while_end -> write__bb0_entry [style=dotted]
	subgraph cluster_print_int {
		label=print_int
		print_int__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ n: int</TD></TR><TR><TD ALIGN="LEFT">01│ v1 : int = 21</TD></TR><TR><TD ALIGN="LEFT">02│ count := %1</TD></TR><TR><TD ALIGN="LEFT">03│ v2 = alloc(%count)</TD></TR><TR><TD ALIGN="LEFT">04│ v3 := %3 as str</TD></TR><TR><TD ALIGN="LEFT">05│ buffer := %4</TD></TR><TR><TD ALIGN="LEFT">06│ v4 : int = 1</TD></TR><TR><TD ALIGN="LEFT">07│ v5 := %count - %6</TD></TR><TR><TD ALIGN="LEFT">08│ i := %7</TD></TR><TR><TD ALIGN="LEFT">09│ v6 := %buffer[%i]</TD></TR><TR><TD ALIGN="LEFT">10│ v7 : int = 10</TD></TR><TR><TD ALIGN="LEFT">11│ %9 = %10</TD></TR><TR><TD ALIGN="LEFT">12│ v8 : int = 1</TD></TR><TR><TD ALIGN="LEFT">13│ v9 := %i - %12</TD></TR><TR><TD ALIGN="LEFT">14│ %i = %13</TD></TR><TR><TD ALIGN="LEFT">15│ v10 : int = 0</TD></TR><TR><TD ALIGN="LEFT">16│ v11 := %n == %15</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">if %16 then $1 else $2</TD></TR>
                    </TABLE>
                > shape=plaintext]
		print_int__bb0_entry -> print_int__bb1_if_then
		print_int__bb0_entry -> print_int__bb3_while
		print_int__bb1_if_then [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb1_if_then</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v12 := %buffer[%i]</TD></TR><TR><TD ALIGN="LEFT">01│ v13 : int = 48</TD></TR><TR><TD ALIGN="LEFT">02│ %0 = %1</TD></TR><TR><TD ALIGN="LEFT">03│ v14 : int = 1</TD></TR><TR><TD ALIGN="LEFT">04│ v15 := %i - %3</TD></TR><TR><TD ALIGN="LEFT">05│ %i = %4</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $2</TD></TR>
                    </TABLE>
                > shape=plaintext]
		print_int__bb1_if_then -> print_int__bb3_while
		print_int__bb3_while [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb3_while</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v16 : int = 0</TD></TR><TR><TD ALIGN="LEFT">01│ v17 := %n != %0</TD></TR><TR><TD ALIGN="LEFT">02│ v18 : int = 0</TD></TR><TR><TD ALIGN="LEFT">03│ v19 := %i != %2</TD></TR><TR><TD ALIGN="LEFT">04│ v20 := %1 and %3</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">if %4 then $3 else $4</TD></TR>
                    </TABLE>
                > shape=plaintext]
		print_int__bb3_while -> print_int__bb3_while_then
		print_int__bb3_while -> print_int__bb4_while_end
		print_int__bb3_while_then [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb3_while_then</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v21 := %buffer[%i]</TD></TR><TR><TD ALIGN="LEFT">01│ v22 : int = 48</TD></TR><TR><TD ALIGN="LEFT">02│ v23 : int = 10</TD></TR><TR><TD ALIGN="LEFT">03│ v24 := %n % %2</TD></TR><TR><TD ALIGN="LEFT">04│ v25 := %1 + %3</TD></TR><TR><TD ALIGN="LEFT">05│ %0 = %4</TD></TR><TR><TD ALIGN="LEFT">06│ v26 : int = 10</TD></TR><TR><TD ALIGN="LEFT">07│ v27 := %n / %6</TD></TR><TR><TD ALIGN="LEFT">08│ %n = %7</TD></TR><TR><TD ALIGN="LEFT">09│ v28 : int = 1</TD></TR><TR><TD ALIGN="LEFT">10│ v29 := %i - %9</TD></TR><TR><TD ALIGN="LEFT">11│ %i = %10</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $2</TD></TR>
                    </TABLE>
                > shape=plaintext]
		print_int__bb3_while_then -> print_int__bb3_while
		print_int__bb4_while_end [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb4_while_end</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v30 := %buffer + %i</TD></TR><TR><TD ALIGN="LEFT">01│ v31 : int = 1</TD></TR><TR><TD ALIGN="LEFT">02│ v32 := %0 + %1</TD></TR><TR><TD ALIGN="LEFT">03│ v33 : int = 1</TD></TR><TR><TD ALIGN="LEFT">04│ v34 := %count - %3</TD></TR><TR><TD ALIGN="LEFT">05│ v35 := %4 - %i</TD></TR><TR><TD ALIGN="LEFT">06│ v36 = write(%STDOUT, %2, %5)</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %6</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
}

:b stderr 0

:b shell 18
cat build/main.dot
:i returncode 0
:b stdout 9069
// Control Flow Graph
digraph {
	subgraph cluster_alloc {
		label=alloc
	}
	"main.sf__bb0_entry" -> print__bb0_entry [style=dotted]
	"main.sf__bb0_entry" -> alloc [style=dotted]
	"main.sf__bb0_entry" -> copy__bb0_entry [style=dotted]
	subgraph "cluster_main.sf" {
		label="main.sf"
		"main.sf__bb0_entry" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v0 : str = Hello world!\n</TD></TR><TR><TD ALIGN="LEFT">01│ a := %0</TD></TR><TR><TD ALIGN="LEFT">02│ v1 := %a.%len</TD></TR><TR><TD ALIGN="LEFT">03│ v2 = print(%a, %2)</TD></TR><TR><TD ALIGN="LEFT">04│ v3 : int = 32</TD></TR><TR><TD ALIGN="LEFT">05│ v4 = alloc(%4)</TD></TR><TR><TD ALIGN="LEFT">06│ v5 := %5 as str</TD></TR><TR><TD ALIGN="LEFT">07│ message := %6</TD></TR><TR><TD ALIGN="LEFT">08│ v6 : str = Hello </TD></TR><TR><TD ALIGN="LEFT">09│ v7 : int = 6</TD></TR><TR><TD ALIGN="LEFT">10│ v8 = copy(%message, %8, %9)</TD></TR><TR><TD ALIGN="LEFT">11│ v9 : int = 6</TD></TR><TR><TD ALIGN="LEFT">12│ v10 := %message + %11</TD></TR><TR><TD ALIGN="LEFT">13│ v11 : str = World </TD></TR><TR><TD ALIGN="LEFT">14│ v12 : int = 6</TD></TR><TR><TD ALIGN="LEFT">15│ v13 = copy(%12, %13, %14)</TD></TR><TR><TD ALIGN="LEFT">16│ v14 : int = 0</TD></TR><TR><TD ALIGN="LEFT">17│ i := %16</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $1</TD></TR>
                    </TABLE>
                > shape=plaintext]
		"main.sf__bb0_entry" -> "main.sf__bb1_while"
		"main.sf__bb1_while" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb1_while</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v15 : int = 10</TD></TR><TR><TD ALIGN="LEFT">01│ v16 := %i &lt; %0</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">if %1 then $2 else $3</TD></TR>
                    </TABLE>
                > shape=plaintext]
		"main.sf__bb1_while" -> "main.sf__bb2_while_then"
		"main.sf__bb1_while" -> "main.sf__bb3_while_end"
		"main.sf__bb2_while_then" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb2_while_then</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v17 : int = 12</TD></TR><TR><TD ALIGN="LEFT">01│ v18 := %i + %0</TD></TR><TR><TD ALIGN="LEFT">02│ v19 := %message[%1]</TD></TR><TR><TD ALIGN="LEFT">03│ v20 : int = 48</TD></TR><TR><TD ALIGN="LEFT">04│ v21 := %3 + %i</TD></TR><TR><TD ALIGN="LEFT">05│ %2 = %4</TD></TR><TR><TD ALIGN="LEFT">06│ v22 : int = 1</TD></TR><TR><TD ALIGN="LEFT">07│ v23 := %i + %6</TD></TR><TR><TD ALIGN="LEFT">08│ %i = %7</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $1</TD></TR>
                    </TABLE>
                > shape=plaintext]
		"main.sf__bb2_while_then" -> "main.sf__bb1_while"
		"main.sf__bb3_while_end" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb3_while_end</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v24 : int = 12</TD></TR><TR><TD ALIGN="LEFT">01│ v25 := %0 + %i</TD></TR><TR><TD ALIGN="LEFT">02│ v26 := %message[%1]</TD></TR><TR><TD ALIGN="LEFT">03│ v27 : int = 10</TD></TR><TR><TD ALIGN="LEFT">04│ %2 = %3</TD></TR><TR><TD ALIGN="LEFT">05│ v28 : int = 12</TD></TR><TR><TD ALIGN="LEFT">06│ v29 := %5 + %i</TD></TR><TR><TD ALIGN="LEFT">07│ v30 : int = 1</TD></TR><TR><TD ALIGN="LEFT">08│ v31 := %6 + %7</TD></TR><TR><TD ALIGN="LEFT">09│ v32 := %message[%8]</TD></TR><TR><TD ALIGN="LEFT">10│ v33 : int = 0</TD></TR><TR><TD ALIGN="LEFT">11│ %9 = %10</TD></TR><TR><TD ALIGN="LEFT">12│ v34 : int = 23</TD></TR><TR><TD ALIGN="LEFT">13│ v35 = print(%message, %12)</TD></TR><TR><TD ALIGN="LEFT">14│ v36 : int = 1</TD></TR><TR><TD ALIGN="LEFT">15│ v37 :: .x = %14</TD></TR><TR><TD ALIGN="LEFT">16│ v38 : int = 7</TD></TR><TR><TD ALIGN="LEFT">17│ v39 :: .a = %16</TD></TR><TR><TD ALIGN="LEFT">18│ v40 : str = Kaboom\n\0</TD></TR><TR><TD ALIGN="LEFT">19│ v41 :: .b = %18</TD></TR><TR><TD ALIGN="LEFT">20│ v42 : int = 1</TD></TR><TR><TD ALIGN="LEFT">21│ v43 :: .y = %20</TD></TR><TR><TD ALIGN="LEFT">22│ v44 := Thing{%15, %17, %19, %21}</TD></TR><TR><TD ALIGN="LEFT">23│ thing := %22</TD></TR><TR><TD ALIGN="LEFT">24│ v45 := %thing.%b</TD></TR><TR><TD ALIGN="LEFT">25│ v46 := %thing.%a</TD></TR><TR><TD ALIGN="LEFT">26│ v47 = print(%24, %25)</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret </TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	subgraph cluster_write {
		label=write
		write__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ fd: int</TD></TR><TR><TD ALIGN="LEFT">01│ buffer: ptr</TD></TR><TR><TD ALIGN="LEFT">02│ count: int</TD></TR><TR><TD ALIGN="LEFT">03│ syscall %SYS_WRITE</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %3</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	subgraph cluster_copy {
		label=copy
		copy__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ destination: str</TD></TR><TR><TD ALIGN="LEFT">01│ source: str</TD></TR><TR><TD ALIGN="LEFT">02│ size: int</TD></TR><TR><TD ALIGN="LEFT">03│ v1 : int = 0</TD></TR><TR><TD ALIGN="LEFT">04│ i := %3</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $1</TD></TR>
                    </TABLE>
                > shape=plaintext]
		copy__bb0_entry -> copy__bb1_while
		copy__bb1_while [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb1_while</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v2 := %i &lt; %size</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">if %0 then $2 else $3</TD></TR>
                    </TABLE>
                > shape=plaintext]
		copy__bb1_while -> copy__bb2_while_then
		copy__bb1_while -> copy__bb3_while_end
		copy__bb2_while_then [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb2_while_then</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ v3 := %destination[%i]</TD></TR><TR><TD ALIGN="LEFT">01│ v4 := %source[%i]</TD></TR><TR><TD ALIGN="LEFT">02│ %0 = %1</TD></TR><TR><TD ALIGN="LEFT">03│ v5 : int = 1</TD></TR><TR><TD ALIGN="LEFT">04│ v6 := %i + %3</TD></TR><TR><TD ALIGN="LEFT">05│ %i = %4</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">jmp $1</TD></TR>
                    </TABLE>
                > shape=plaintext]
		copy__bb2_while_then -> copy__bb1_while
		copy__bb3_while_end [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb3_while_end</B></TD></TR>
                        
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret </TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
	print__bb0_entry -> write__bb0_entry [style=dotted]
	subgraph cluster_print {
		label=print
		print__bb0_entry [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        <TR><TD ALIGN="LEFT">00│ message: str</TD></TR><TR><TD ALIGN="LEFT">01│ size: int</TD></TR><TR><TD ALIGN="LEFT">02│ v1 := %message as ptr</TD></TR><TR><TD ALIGN="LEFT">03│ v2 = write(%STDOUT, %2, %size)</TD></TR>
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret %3</TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
}

:b stderr 0

:b shell 19
cat build/macos.dot
:i returncode 0
:b stdout 513
// Control Flow Graph
digraph {
	subgraph "cluster_macos.sf" {
		label="macos.sf"
		"macos.sf__bb0_entry" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret </TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
}

:b stderr 0

:b shell 18
cat build/core.dot
:i returncode 0
:b stdout 510
// Control Flow Graph
digraph {
	subgraph "cluster_core.sf" {
		label="core.sf"
		"core.sf__bb0_entry" [label=<
                    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0">
                        <TR><TD BGCOLOR="lightgray"><B>bb0_entry</B></TD></TR>
                        
                        
                        <TR><TD BGCOLOR="black" HEIGHT="1"></TD></TR>
                        <TR><TD ALIGN="LEFT">ret </TD></TR>
                    </TABLE>
                > shape=plaintext]
	}
}

:b stderr 0

