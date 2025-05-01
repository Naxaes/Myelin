# MACHO = """
# ; A minimal Mach-o x64 executable for OS X Sierra
# ; $ nasm -f bin -o tiny_hello tiny_hello.s && chmod +x tiny_hello
# ; https://www.mikeash.com/pyblog/friday-qa-2012-11-30-lets-build-a-mach-o-executable.html
# ; https://stackoverflow.com/a/32659692
# ; https://github.com/aidansteele/osx-abi-macho-file-format-reference
# ; https://www.youtube.com/watch?v=rg6kU42LQcY&ab_channel=HackVlix
#
#
# ; Constants (For readability)
# %define MH_MAGIC_64                     0xfeedfacf
# %define CPU_ARCH_ABI64                  0x01000000
# %define CPU_TYPE_I386                   0x00000007
# %define CPU_TYPE_X86_64                 CPU_ARCH_ABI64 | CPU_TYPE_I386
# %define CPU_SUBTYPE_LIB64               0x80000000
# %define CPU_SUBTYPE_I386_ALL            0x00000003
# %define MH_EXECUTE                      0x2
# %define MH_NOUNDEFS                     0x1
# %define LC_SEGMENT_64                   0x19
# %define LC_UNIXTHREAD                   0x5
# %define VM_PROT_READ                    0x1
# %define VM_PROT_WRITE                   0x2
# %define VM_PROT_EXECUTE                 0x4
# %define x86_THREAD_STATE64              0x4
# %define x86_EXCEPTION_STATE64_COUNT     42
# ; https://stackoverflow.com/a/53905561
# %define SYSCALL_CLASS_SHIFT             24
# %define SYSCALL_CLASS_MASK              (0xFF << SYSCALL_CLASS_SHIFT)
# %define SYSCALL_NUMBER_MASK             (~SYSCALL_CLASS_MASK)
# %define SYSCALL_CLASS_UNIX              2
# %define SYSCALL_CONSTRUCT_UNIX(syscall_number) ((SYSCALL_CLASS_UNIX << SYSCALL_CLASS_SHIFT) | (SYSCALL_NUMBER_MASK & (syscall_number)))
# %define SYS_exit                        1
# %define SYS_write                       4
#
#
#
# ; NASM directive, not compiled
# ; Use RIP-Relative addressing for x64
# BITS 64
# %define ORIGIN 0x100000000
# org ORIGIN
#
# ; Mach-O header
# 	dd MH_MAGIC_64                                      ; magic
# 	dd CPU_TYPE_X86_64                                  ; cputype
# 	dd CPU_SUBTYPE_LIB64 | CPU_SUBTYPE_I386_ALL         ; cpusubtype
# 	dd MH_EXECUTE                                       ; filetype
# 	dd 3                                                ; ncmds
# 	dd __COMMANDSend - __COMMANDSstart                  ; sizeofcmds
# 	dd MH_NOUNDEFS                                      ; flags
# 	dd 0x0                                              ; reserved
#
# __COMMANDSstart:
#
# __PAGEZEROstart:
# 	dd LC_SEGMENT_64                                    ; cmd
# 	dd __PAGEZEROend - __PAGEZEROstart                  ; command size
# 	db '__PAGEZERO', 0, 0, 0, 0, 0, 0                   ; segment name (pad to 16 bytes)
# 	dq 0                                                ; vmaddr
# 	dq ORIGIN                                           ; vmsize
# 	dq 0                                                ; fileoff
# 	dq 0                                                ; filesize
# 	dd 0                                                ; maxprot
# 	dd 0                                                ; initprot
# 	dd 0                                                ; nsects
# 	dd 0                                                ; flags
# __PAGEZEROend:
#
# ; Segment and Sections
# __TEXTstart:
# 	dd LC_SEGMENT_64                                    ; cmd
# 	dd __TEXTend - __TEXTstart                          ; command size
# 	db '__TEXT', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0           ; segment name (pad to 16 bytes)
# 	dq ORIGIN                                           ; vmaddr
# 	dq __codeend - ORIGIN                               ; vmsize
# 	dq 0                                                ; fileoff
# 	dq __codeend - ORIGIN                               ; filesize
# 	dd VM_PROT_READ | VM_PROT_WRITE | VM_PROT_EXECUTE   ; maxprot
# 	dd VM_PROT_READ | VM_PROT_WRITE | VM_PROT_EXECUTE                   ; initprot
# 	dd 0                                                ; nsects
# 	dd 0                                                ; flags
# __TEXTend:
#
# ; UNIX Thread Status
# __UNIX_THREADstart:
# 	dd LC_UNIXTHREAD                            ; cmd
# 	dd __UNIX_THREADend - __UNIX_THREADstart    ; cmdsize
# 	dd x86_THREAD_STATE64                       ; flavor
# 	dd x86_EXCEPTION_STATE64_COUNT              ; count
# 	dq 0, 0, 0, 0                               ; rax, rbx, rcx, rdx
# 	dq 0, 0, 0, 0                               ; rdi, rsi, rbp, rsp
# 	dq 0, 0, 0, 0                               ; r8, r9, r10, r11
# 	dq 0, 0, 0, 0                               ; r12, r13, r14, r15
# 	dq __codestart, 0, 0, 0, 0                  ; rip, rflags, cs, fs, gs
# __UNIX_THREADend:
#
# __COMMANDSend:
#
# __codestart:
#
#     {code}
#
# __codeend:
#
# ; Pad executable to the minimum required 4Kb
# times 4096-($-$$) db 0
# """


INTERNAL_CODE = """\
; ---- Built-ins ----
; void* {rax} alloc(int size {rax})
alloc:
    mov rdi, [rel memory.ptr]       ; Load current pointer (offset in bytes)

    lea rsi, [rel memory.start]     ; Load base address
    lea rdx, [rel memory.end]       ; Load end address

    lea r8, [rsi + rdi]             ; r8 = allocated address (base + offset)
    lea r9, [r8 + rax]              ; r9 = address after allocation

    cmp r9, rdx                     ; if (new_address > memory_end)
    ja .error                       ;     goto .error

    lea r10, [rel memory.ptr]
    add [r10], rax                  ; Update memory pointer
    mov rax, r8                     ; Return allocated pointer
    ret

.error:
    mov rdi, 123                    ; exit code
    mov rax, 0x2000001              ; SYS_exit
    syscall

"""
INTERNAL_DATA = """
section .data
align 4
memory:
.ptr: dq 0                          ; Offset (in bytes)
.start:
    times 128 dq 0
.end:
"""


import os


def le16(n):
  return [
    n & 0xFF,
    (n >> 8) & 0xFF
  ]


def le32(n):
  return [
    n & 0xFF,
    (n >> 8) & 0xFF,
    (n >> 16) & 0xFF,
    (n >> 24) & 0xFF
  ]


def le64(n):
  return [
    n & 0xFF,
    (n >> 8) & 0xFF,
    (n >> 16) & 0xFF,
    (n >> 24) & 0xFF,
    (n >> 32) & 0xFF,
    (n >> 40) & 0xFF,
    (n >> 48) & 0xFF,
    (n >> 56) & 0xFF
  ]


MH_MAGIC_64                 = 0xfeedfacf
CPU_ARCH_ABI64              = 0x01000000
CPU_TYPE_I386               = 0x00000007
CPU_TYPE_X86_64             = CPU_ARCH_ABI64 | CPU_TYPE_I386
CPU_SUBTYPE_LIB64           = 0x80000000
CPU_SUBTYPE_I386_ALL        = 0x00000003
MH_EXECUTE                  = 0x2
MH_NOUNDEFS                 = 0x1
LC_SEGMENT_64               = 0x19
LC_UNIXTHREAD               = 0x5
VM_PROT_READ                = 0x1
VM_PROT_WRITE               = 0x2
VM_PROT_EXECUTE             = 0x4
x86_THREAD_STATE64          = 0x4
x86_EXCEPTION_STATE64_COUNT = 42


def pad_byte_string(string: str, size):
    return [*string.encode()] + [0] * (size-len(string))


def macho_header(command_count, command_size):
    #   dd MH_MAGIC_64                                      ; magic
    # 	dd CPU_TYPE_X86_64                                  ; cputype
    # 	dd CPU_SUBTYPE_LIB64 | CPU_SUBTYPE_I386_ALL         ; cpusubtype
    # 	dd MH_EXECUTE                                       ; filetype
    # 	dd 3                                                ; ncmds
    # 	dd __COMMANDSend - __COMMANDSstart                  ; sizeofcmds
    # 	dd MH_NOUNDEFS                                      ; flags
    # 	dd 0x0                                              ; reserved
    return [
        *le32(MH_MAGIC_64),
        *le32(CPU_TYPE_X86_64),
        *le32(CPU_SUBTYPE_LIB64 | CPU_SUBTYPE_I386_ALL),
        *le32(MH_EXECUTE),
        *le32(command_count),
        *le32(command_size),
        *le32(MH_NOUNDEFS),
        *le32(0)
    ]

def macho_page_zero(origin):
    #   __PAGEZEROstart:
    # 	dd LC_SEGMENT_64                                    ; cmd
    # 	dd __PAGEZEROend - __PAGEZEROstart                  ; command size
    # 	db '__PAGEZERO', 0, 0, 0, 0, 0, 0                   ; segment name (pad to 16 bytes)
    # 	dq 0                                                ; vmaddr
    # 	dq ORIGIN                                           ; vmsize
    # 	dq 0                                                ; fileoff
    # 	dq 0                                                ; filesize
    # 	dd 0                                                ; maxprot
    # 	dd 0                                                ; initprot
    # 	dd 0                                                ; nsects
    # 	dd 0                                                ; flags
    # __PAGEZEROend:
    return [
        *le32(LC_SEGMENT_64),
        *le32(72),
        *pad_byte_string('__PAGEZERO', 16),
        *le64(0),
        *le64(origin),
        *le64(0),
        *le64(0),
        *le32(0),
        *le32(0),
        *le32(0),
        *le32(0),
    ]


def macho_text(origin, size):
    # __TEXTstart:
    # 	dd LC_SEGMENT_64                                    ; cmd
    # 	dd __TEXTend - __TEXTstart                          ; command size
    # 	db '__TEXT', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0           ; segment name (pad to 16 bytes)
    # 	dq ORIGIN                                           ; vmaddr
    # 	dq __codeend - ORIGIN                               ; vmsize
    # 	dq 0                                                ; fileoff
    # 	dq __codeend - ORIGIN                               ; filesize
    # 	dd VM_PROT_READ | VM_PROT_WRITE | VM_PROT_EXECUTE   ; maxprot
    # 	dd VM_PROT_READ | VM_PROT_EXECUTE                   ; initprot
    # 	dd 0                                                ; nsects
    # 	dd 0                                                ; flags
    # __TEXTend:
    return [
        *le32(LC_SEGMENT_64),
        *le32(72),
        *pad_byte_string('__TEXT', 16),
        *le64(origin),
        *le64(size),
        *le64(0),
        *le64(size),
        *le32(VM_PROT_READ | VM_PROT_WRITE | VM_PROT_EXECUTE),
        *le32(VM_PROT_READ | VM_PROT_WRITE | VM_PROT_EXECUTE),
        *le32(0),
        *le32(0),
    ]

def macho_start(entry):
    # __UNIX_THREADstart:
    # 	dd LC_UNIXTHREAD                            ; cmd
    # 	dd __UNIX_THREADend - __UNIX_THREADstart    ; cmdsize
    # 	dd x86_THREAD_STATE64                       ; flavor
    # 	dd x86_EXCEPTION_STATE64_COUNT              ; count
    # 	dq 0, 0, 0, 0                               ; rax, rbx, rcx, rdx
    # 	dq 0, 0, 0, 0                               ; rdi, rsi, rbp, rsp
    # 	dq 0, 0, 0, 0                               ; r8, r9, r10, r11
    # 	dq 0, 0, 0, 0                               ; r12, r13, r14, r15
    # 	dq __codestart, 0, 0, 0, 0                  ; rip, rflags, cs, fs, gs
    # __UNIX_THREADend:
    return [
        *le32(LC_UNIXTHREAD),
        *le32(184),
        *le32(x86_THREAD_STATE64),
        *le32(x86_EXCEPTION_STATE64_COUNT),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(entry),
        *le64(0),
        *le64(0),
        *le64(0),
        *le64(0),
    ]


def round_up_to_multiple_of_two(number, multiple):
    return (number + multiple - 1) & -multiple

def make_macho_executable(output, code, data):
    origin = 0x100000000

    head_s = 32
    zero_s = 72
    text_s = 72
    start_s = 184
    all_header_s = head_s + zero_s + text_s + start_s

    entry = origin + all_header_s

    header = f'BITS 64\norg {entry}\n'
    program = header+code+INTERNAL_CODE+INTERNAL_DATA+data

    with open(f'build/{output}.s', 'w') as file:
        file.write(program)
    os.system(f'nasm -f bin -o build/{output} build/{output}.s && chmod +x build/{output}')
    binary = open(f'build/{output}', 'rb').read()

    zero  = macho_page_zero(origin)
    start = macho_start(entry)
    text  = macho_text(origin,  all_header_s + len(binary))
    head  = macho_header(3, len(zero) + len(start) + len(text))

    executable = bytes(head + zero + text + start) + binary
    result = executable + bytes([0] * (4096-len(executable)))  # Pad

    with open(f'build/{output}', 'wb') as file:
        file.write(result)

    return result, program


# def create_macho_executable(output, code):
#     with open(f'build/{output}.s', 'w') as file:
#         file.write(MACHO.format(code=code))
#
#     os.system(f'nasm -f bin -o build/{output} build/{output}.s && chmod +x build/{output}')
#
#     return open(f'build/{output}', 'rb').read()

#
# a = create_macho_executable('temp_a', """
#     mov rdi, 0x01
#     mov rsi, hello_str
#     mov rdx, hello_str.size
#     mov rax, 0x2000000+4
#     syscall
#
#     mov rdi, rax
#     mov rax, 0x2000000+1
#     syscall
#
# hello_str:
# 	db "Hello world", 10, 0
# 	.size equ $ - hello_str
# """)
# b = macho_executable('temp_b', """
#     mov rdi, 0x01
#     mov rsi, hello_str
#     mov rdx, hello_str.size
#     mov rax, 0x2000000+4
#     syscall
#
#     mov rdi, rax
#     mov rax, 0x2000000+1
#     syscall
#
# hello_str:
# 	db "Hello world", 10, 0
# 	.size equ $ - hello_str
# """)


