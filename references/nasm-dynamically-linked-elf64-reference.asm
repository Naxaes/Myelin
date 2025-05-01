; An eager dynamically linked elf64 executable linking to libc and pthread.
; $ nasm nasm-dynamically-linked-elf64-reference.asm -f bin -o nasm-dynamically-linked-elf64-reference.out
; $ chmod +x nasm-dynamically-linked-elf64-reference.out

use64

%define SYS_EXIT 60


BASE: equ 0x400000
org BASE


; ==== EFL64 HEADER ====
elf64_header:
	db 0x7F, "ELF"                          ; Magic number to indicate ELF file
	db 2                                    ; 1 for 32-bit, 2 for 64-bit
	db 1                                    ; 1 for little endian, 0x2 for big endian
	db 1                                    ; 1 for current version of ELF
	db 0                                    ; 9 for FreeBSD, 3 for Linux (doesn't seem to matter)
	db 0                                    ; ABI version (ignored?)
	times 7 db 0                            ; 7 padding bytes
	dw 2                                    ; ET_EXEC
    dw 0x3E                                 ; AMD x86-64
    dd 1                                    ; EV_CURRENT
    dq _start                               ; Entry point
    dq elf64_program_headers-BASE           ; Program header offset
    dq elf64_section_headers-BASE           ; Section header offset
    dd 0                                    ; Flags
    dw elf64_header.size                    ; ELF header size
    dw elf64_program_headers.entry_size     ; Program header entry size
    dw elf64_program_headers.count          ; Number of program headers
    dw elf64_section_headers.entry_size     ; Section header entry size
    dw elf64_section_headers.count          ; Number of section headers
    dw 1                                    ; Index of the section header table entry that contains the section names
.size equ $-elf64_header


; ==== PROGRAM HEADERS ====
%define PT_LOAD     1
%define PT_INTERP   3
%define PT_DYNAMIC  4
%define PT_PHDR     6

elf64_program_headers:
	; PT_PHDR
	dd 6
	dd 4
	dq elf64_program_headers - BASE
	dq elf64_program_headers
	dq 0
	dq elf64_program_headers.size
	dq elf64_program_headers.size
	dq 8

	; PT_INTERP
	dd 3
	dd 4
	dq interpreter - BASE
	dq interpreter
	dq 0
	dq interpreter.size
	dq interpreter.size
	dq 8

	; PT_DYNAMIC
	dd 2
	dd 4
	dq dynamic_table - BASE
	dq dynamic_table
	dq 0
	dq dynamic_table.size
	dq dynamic_table.size
	dq 8

	; PT_LOAD
	dd 1
	dd 5
	dq elf64_header - BASE
	dq BASE
	dq 0
	dq FILE_SIZE
	dq FILE_SIZE
	dq 0x100000
.entry_size: equ 56                             ; Always 56 bytes for 64-bit version
.size: equ $-elf64_program_headers
.count equ elf64_program_headers.size / elf64_program_headers.entry_size


; ==== SECTION HEADERS ====
%define SHT_PROGBITS    0x1
%define SHT_SYMTAB      0x2
%define SHT_STRTAB      0x3
%define SHT_RELA        0x4
%define SHT_DYNAMIC     0x6
%define SHT_DYNSYM      0xB

elf64_section_headers:
		; Null entry
        dd 0                                ; sh_name;
        dd 0                                ; sh_type;
        dq 0                                ; sh_flags;
        dq 0                                ; sh_addr;
        dq 0                                ; sh_offset;
        dq 0                                ; sh_size;
        dd 0                                ; sh_link;
        dd 0                                ; sh_info;
        dq 0                                ; sh_addralign;
        dq 0                                ; sh_entsize;

        dd string_table.dynstr                                ; sh_name;
        dd SHT_STRTAB                       ; sh_type;
        dq 0                                ; sh_flags;
        dq 0                                ; sh_addr;
        dq string_table-BASE       ; sh_offset;
        dq string_table.size                                ; sh_size;
        dd 0                                ; sh_link;
        dd 0                                ; sh_info;
        dq 1                                ; sh_addralign;
        dq 0                                ; sh_entsize;

		dd string_table.dynamic                                ; sh_name;
        dd SHT_DYNAMIC                       ; sh_type;
        dq 2                                ; sh_flags;
        dq 0                                ; sh_addr;
        dq dynamic_table-BASE       ; sh_offset;
        dq dynamic_table.size                                ; sh_size;
        dd 1                                ; sh_link  link to SHT_STRTAB https://github.com/bminor/binutils-gdb/blob/343776af14932fa6b6f8f5b731c097758a6a2049/binutils/readelf.c#L8537C1-L8538C1
        dd 0                                ; sh_info;
        dq 8                                ; sh_addralign;
        dq 16                               ; sh_entsize;

        dd string_table.dynsym                                ; sh_name;
        dd SHT_DYNSYM                       ; sh_type;
        dq 2                                ; sh_flags;
        dq symbol_table                                ; sh_addr;
        dq symbol_table-BASE       ; sh_offset;
        dq symbol_table.size                                ; sh_size;
        dd 1                                ; sh_link  link to SHT_STRTAB https://github.com/bminor/binutils-gdb/blob/343776af14932fa6b6f8f5b731c097758a6a2049/binutils/readelf.c#L8537C1-L8538C1
        dd 0                                ; sh_info;
        dq 8                                ; sh_addralign;
        dq 24                               ; sh_entsize;

        dd string_table.rela                                ; sh_name;
        dd SHT_RELA                       ; sh_type;
        dq 2                                ; sh_flags;
        dq relocation_table                                ; sh_addr;
        dq relocation_table-BASE       ; sh_offset;
        dq relocation_table.size                                ; sh_size;
        dd 3                                ; sh_link  link to SHT_DYNSYM
        dd 0                                ; sh_info;
        dq 8                                ; sh_addralign;
        dq 24                               ; sh_entsize;

        dd string_table.text                                ; sh_name;
        dd SHT_PROGBITS                       ; sh_type;
        dq 2                                ; sh_flags;
        dq code_start                                ; sh_addr;
        dq code_start-BASE       ; sh_offset;
        dq code_end-code_start                                ; sh_size;
        dd 0                                ; sh_link  link to SHT_DYNSYM
        dd 0                                ; sh_info;
        dq 4096                                ; sh_addralign;
        dq 0                               ; sh_entsize;

        dd string_table.data                                ; sh_name;
        dd SHT_PROGBITS                       ; sh_type;
        dq 2                                ; sh_flags;
        dq data_start                                ; sh_addr;
        dq data_start-BASE       ; sh_offset;
        dq data_end-data_start                                ; sh_size;
        dd 0                                ; sh_link  link to SHT_DYNSYM
        dd 0                                ; sh_info;
        dq 8                                ; sh_addralign;
        dq 0                               ; sh_entsize;

.entry_size: equ 64                             ; Always 64 bytes for 64-bit version
.size: equ $-elf64_section_headers
.count equ elf64_section_headers.size / elf64_section_headers.entry_size


; ==== CODE ====
align 4096
code_start:
_start:
	xor     r12, r12

_create_thread:
	cmp     r12d, 10
    je      _exit
	inc     r12

    xor     rsi, rsi
    push    rax
    mov     rdi, rsp
    mov     edx, _thread_routine_
	mov     rcx, r12
	call    [_pthread_create_]
	test    rax, rax
    pop     rax
    jnz     _exit_error
    jmp     _create_thread

_exit_error:
	mov     edi, error_msg
	call    [_printf_]
_exit:
	mov     rdi, rax
	mov     rsi, 0
	call    [_pthread_join_]

	mov     edi, 33
	call    [_exit_]

; void thread_routine(void *);
_thread_routine_:
	mov     rsi, rdi            ; pthread arg
	mov     rdx, [fs:0]         ; fs points to Thread Information Block (offset 0 is the thread pointer) - https://stackoverflow.com/questions/65323028/thread-local-real-usage-of-the-underlying-segment-registers, https://stackoverflow.com/questions/10810203/what-is-the-fs-gs-register-intended-for
	mov     edi, thread_msg
	xor     eax, eax
	call    [_printf_]
	ret

code_end:

; ==== DATA ====
data_start:
thread_msg db "Thread %d with thread pointer = %p", 10, 0
error_msg  db "pthread_create fails with error %d", 10, 0
data_end:

align 8
_printf_                dq 0
_pthread_create_        dq 0
_pthread_join_          dq 0
_exit_                  dq 0


; ==== DYNAMIC ====
align 8
dynamic_table:
	dq 1, string_table.libc           ;DT_NEEDED
	dq 1, string_table.libpthread       ;DT_NEEDED
	dq 5, string_table                    ;DT_STRTAB
	dq 6, symbol_table                    ;DT_SYMTAB
	dq 10, string_table.size              ;DT_STRSZ
	dq 11, 24                               ;DT_SYMENT
	dq 7, relocation_table                      ;DT_RELA
	dq 8, relocation_table.size           ;DT_RELASZ
	dq 9, 24                            ;DT_RELAENT
	dq 0, 0                          ;terminator
.size: equ $-dynamic_table


; === DYNAMIC STRING TABLE ===
string_table:
.null: equ $-string_table
	db 0
.libc: equ $-string_table
	db "libc.so.6", 0
.libpthread: equ $-string_table
	db "libpthread.so.0", 0
.printf: equ $-string_table
	db "printf", 0
.pthread_create: equ $-string_table
	db "pthread_create", 0
.pthread_join: equ $-string_table
	db "pthread_join", 0
.exit: equ $-string_table
	db "exit", 0
.dynstr: equ $-string_table
	db ".dynstr", 0
.dynamic: equ $-string_table
	db ".dynamic", 0
.text: equ $-string_table
	db ".text", 0
.data: equ $-string_table
	db ".data", 0
.dynsym: equ $-string_table
	db ".dynsym", 0
.rela: equ $-string_table
	db ".rela", 0
.size: equ $-string_table


; === DYNAMIC SYMBOL TABLE ===
align 4
symbol_table_entry_size equ 24
symbol_table:
.null: equ ($ - symbol_table) / symbol_table_entry_size
	times symbol_table_entry_size db 0
.printf: equ ($ - symbol_table) / symbol_table_entry_size
	dd string_table.printf      ;strtab_index
    db (1 << 4) + 2          ;info=GLOBAL,STT_FUNCTION
    db 0                    ;other
	dw 0                    ;shndx=SHN_UNDEF
	dq 0
	dq 0                 ;value=unknown,size=unknown
.pthread_create: equ ($ - symbol_table) / symbol_table_entry_size
    dd string_table.pthread_create
	db (1 << 4) + 2          ;GLOBAL,STT_FUNCTION
	db 0
	dw 0
	dq 0
	dq 0
.pthread_join: equ ($ - symbol_table) / symbol_table_entry_size
    dd string_table.pthread_join
	db (1 << 4) + 2          ;GLOBAL,STT_FUNCTION
	db 0
	dw 0
	dq 0
	dq 0
.exit: equ ($ - symbol_table) / symbol_table_entry_size
    dd string_table.exit
	db (1 << 4) + 2          ;GLOBAL,STT_FUNCTION
	db 0
	dw 0
	dq 0
	dq 0
.size: equ $-symbol_table


; === RELOCATION TABLE (RELA) ===
align 8
relocation_table:
.printf:
	dq _printf_
	dq (symbol_table.printf << 32) + (1 & 0xffffffff)
    dq 0
.pthread_create:
	dq _pthread_create_
	dq (symbol_table.pthread_create << 32) + (1 & 0xffffffff)
	dq 0
.pthread_join:
	dq _pthread_join_
	dq (symbol_table.pthread_join << 32) + (1 & 0xffffffff)
	dq 0
.exit:
	dq _exit_
	dq (symbol_table.exit << 32) + (1 & 0xffffffff)
	dq 0
.size: equ $-relocation_table


; === INTERPRETER ===
interpreter:
    db "/lib64/ld-linux-x86-64.so.2", 0
.size: equ $-interpreter


FILE_SIZE: equ $-BASE
