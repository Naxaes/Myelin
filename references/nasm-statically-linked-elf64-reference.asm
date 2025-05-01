; A static elf64 executable.
; $ nasm nasm-dynamically-linked-elf64-reference.asm -f bin -o nasm-dynamically-linked-elf64-reference.out
; $ chmod +x nasm-dynamically-linked-elf64-reference.out

use64

BASE: equ 0x400000
org BASE

MEMORY_SIZE: equ 0                          ; Any additional memory allocated after the data section


; ==== EFL64 HEADER ====
elf64_header:
	db 0x7F, "ELF"                          ; magic number to indicate ELF file
	db 2                                    ; 1 for 32-bit, 2 for 64-bit
	db 1                                    ; 1 for little endian, 0x2 for big endian
	db 1                                    ; 1 for current version of ELF
	db 3                                    ; 9 for FreeBSD, 3 for Linux (doesn't seem to matter)
	db 0                                    ; ABI version (ignored?)
	times 7 db 0                            ; 7 padding bytes
	dw 2                                    ; ET_EXEC
	dw 0x003E                               ; AMD x86-64
	dd 1                                    ; version 1
	dq _code_start                          ; entry point for our program
	dq elf64_program_headers-BASE           ; 0x40 offset from ELF_HEADER to PROGRAM_HEADER
	dq 0                                    ; section header offset (we don't have this)
	dd 0                                    ; unused flags
	dw elf64_header.size                    ; 64-byte size of ELF_HEADER
	dw elf64_program_headers.entry_size     ; 56-byte size of each program header entry
	dw elf64_program_headers.count          ; number of program header entries (we have one)
	dw 0                                    ; size of each section header entry (none)
	dw 0                                    ; number of section header entries (none)
	dw 0                                    ; index in section header table for section names (waste)
.size equ $-elf64_header


; ==== PROGRAM HEADERS ====
elf64_program_headers:
	dd 1                                    ; 1 for loadable program segment
	dd 7                                    ; read/write/execute flags
	dq _code_start-BASE                     ; offset of code start in file image (0x40+0x38)
	dq _code_start                          ; virtual address of segment in memory
	dq 0                                    ; physical address of segment in memory (ignored?)
	dq FILE_SIZE                            ; size (bytes) of segment in file image
	dq FILE_SIZE+MEMORY_SIZE                ; size (bytes) of segment in memory
	dq 0x0000000000000000                   ; alignment (doesn't matter, only 1 segment)
.entry_size: equ 56                             ; Always 56 bytes for 64-bit version
.size: equ $-elf64_program_headers
.count equ elf64_program_headers.size / elf64_program_headers.entry_size


; ==== SECTION HEADERS ====
elf64_section_headers:
.entry_size: equ 64                             ; Always 64 bytes for 64-bit version
.size: equ $-elf64_section_headers
.count equ elf64_section_headers.size / elf64_section_headers.entry_size


; ==== CODE ====
_code_start:
	mov rdi, 1              ; STDOUT
	mov rsi, message
	mov rdx, message.size
	mov rax, 4              ; `write` syscall
	syscall

	mov rdi, 69
	mov rax, 60  ; SYS_EXIT
	syscall
_code_end:


; ==== DATA ====
_data_start:
	message db "Hello world!", 10, 0
		.size equ $-message
_data_end:


; ==== OTHER ====
FILE_SIZE: equ _data_end - _code_start