# https://github.com/apple/darwin-xnu/blob/main/EXTERNAL_HEADERS/mach-o/loader.h
# https://github.com/corkami/pics
# https://lief.re/doc/latest/intro.html
# https://en.wikipedia.org/wiki/Mach-O#


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
align 4096
memory:
.ptr: dq 0                          ; Offset (in bytes)
.start:
    times 128 db 100, 101, 98, 117, 103, 109, 101, 109      ; 'debugmem'
.end:
"""
PAD_DATA = """
; Pad executable to the minimum required 4Kb
times 4096-($-memory) db 0
"""


import subprocess


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


HEADER_SIZE     = 32
CMD_SIZE        = 72
SECT_SIZE       = 80
START_CMD_SIZE  = 184



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


def section(name, address, size, offset):
#   struct section_64 { /* for 64-bit architectures */
# 	char		sectname[16];	/* name of this section */
# 	char		segname[16];	/* segment this section goes in */
# 	uint64_t	addr;		/* memory address of this section */
# 	uint64_t	size;		/* size in bytes of this section */
# 	uint32_t	offset;		/* file offset of this section */
# 	uint32_t	align;		/* section alignment (power of 2) */
# 	uint32_t	reloff;		/* file offset of relocation entries */
# 	uint32_t	nreloc;		/* number of relocation entries */
# 	uint32_t	flags;		/* flags (section type and attributes)*/
# 	uint32_t	reserved1;	/* reserved (for offset or index) */
# 	uint32_t	reserved2;	/* reserved (for count or sizeof) */
# 	uint32_t	reserved3;	/* reserved */
# };
    align = 1
    reloff = 0
    nreloc = 0
    flags  = 0
    return [
        *pad_byte_string(name.lower(), 16),
        *pad_byte_string(name.upper(), 16),
        *le64(address),
        *le64(size),
        *le32(offset),
        *le32(align),
        *le32(reloff),
        *le32(nreloc),
        *le32(flags),
        *le32(0),
        *le32(0),
        *le32(0),
    ]


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


def macho_load_command(name, origin, size):
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
    # cmd_size = 72
    cmd_size = 72 + 80
    offset = HEADER_SIZE + CMD_SIZE + 2*(CMD_SIZE+SECT_SIZE) + START_CMD_SIZE
    return [
        *le32(LC_SEGMENT_64),
        *le32(cmd_size),
        *pad_byte_string(name.upper(), 16),
        *le64(origin if name == '__TEXT' else origin + 4096),
        *le64(size),
        *le64(HEADER_SIZE+CMD_SIZE if name == '__TEXT' else HEADER_SIZE+CMD_SIZE+CMD_SIZE+SECT_SIZE),
        *le64(CMD_SIZE+SECT_SIZE),
        *le32(VM_PROT_READ | VM_PROT_EXECUTE if name == '__TEXT' else VM_PROT_READ | VM_PROT_WRITE),
        *le32(VM_PROT_READ | VM_PROT_EXECUTE if name == '__TEXT' else VM_PROT_READ | VM_PROT_WRITE),
        *le32(1),
        *le32(0),
        *section(name, origin, size-offset, offset if name == '__TEXT' else  4096)
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

# %rdi, %rsi, %rdx, %rcx, %r8 and %r9
def make_macho_executable(output, code, data, generate_debug=False):
    origin = 0x100000000

    head_s = 32
    zero_s = 72
    text_s = 72+80
    data_s = 72+80
    start_s = 184
    all_header_s = head_s + zero_s + text_s + data_s + start_s

    entry = origin + all_header_s

    header = f'BITS 64\norg {entry}\n'
    program = header+code+INTERNAL_CODE+INTERNAL_DATA+data+PAD_DATA

    subprocess.run(['mkdir', '-p', 'build'])
    with open(f'build/{output}.s', 'w') as file:
        file.write(program)

    # Code binary
    status = subprocess.run(['nasm', '-f', 'bin', '-w+all', '-o', f'build/{output}', f'build/{output}.s'], capture_output=True)
    if status.returncode != 0: raise RuntimeError(f'Nasm failed with status code {status.args}:\n{status.stdout}\n{status.stderr}' )
    status = subprocess.run(['chmod', '+x', f'build/{output}'], capture_output=True)
    if status.returncode != 0: raise RuntimeError(f'Nasm failed with status code {status.args}:\n{status.stdout}\n{status.stderr}' )
    binary = open(f'build/{output}', 'rb').read()

    # Debug code
    if generate_debug:
        header = f'BITS 64\nglobal _start\n_start:\n'
        debug = header + code + INTERNAL_CODE + INTERNAL_DATA + data + PAD_DATA
        with open(f'build/{output}_debug.s', 'w') as file:
            file.write(debug)
        subprocess.run(['nasm', '-f', 'macho64', '-g', '-F', 'dwarf', '-w+all', f'build/{output}_debug.s', '-o', f'build/{output}_debug.o', '&&', 'ld', '-macos_version_min', '11.0', '-L', '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/lib/', '-lSystem', '-o', f'build/{output}_debug', '-e', '_start', f'build/{output}_debug.o'], capture_output=True)

    zero  = [
        *le32(LC_SEGMENT_64),
        *le32(CMD_SIZE),
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
    offset = len(zero)
    text  = [
        *le32(LC_SEGMENT_64),
        *le32(CMD_SIZE + SECT_SIZE),
        *pad_byte_string('__TEXT', 16),
        *le64(origin),
        *le64(4096),
        *le64(0),
        *le64(4096),
        *le32(VM_PROT_READ | VM_PROT_EXECUTE),
        *le32(VM_PROT_READ | VM_PROT_EXECUTE),
        *le32(1),
        *le32(0),
        # Section 1
        *pad_byte_string('__text', 16),
        *pad_byte_string('__TEXT', 16),
        *le64(origin+all_header_s),
        *le64(4096-all_header_s),
        *le32(all_header_s),
        *le32(1),
        *le32(0),
        *le32(0),
        *le32(0),
        *le32(0),
        *le32(0),
        *le32(0),
    ]
    data_ = [
        *le32(LC_SEGMENT_64),
        *le32(CMD_SIZE+SECT_SIZE),
        *pad_byte_string('__DATA', 16),
        *le64(origin+4096),
        *le64(4096),
        *le64(4096),
        *le64(4096),
        *le32(VM_PROT_READ | VM_PROT_WRITE),
        *le32(VM_PROT_READ | VM_PROT_WRITE),
        *le32(1),
        *le32(0),
        # Section 1
        *pad_byte_string('__data', 16),
        *pad_byte_string('__DATA', 16),
        *le64(origin+4096),
        *le64(4096),
        *le32(4096),
        *le32(1),
        *le32(0),
        *le32(0),
        *le32(0),
        *le32(0),
        *le32(0),
        *le32(0),
    ]
    start = [
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
    command_size = len(zero) + len(text) + len(data_) + len(start)
    head  = [
        *le32(MH_MAGIC_64),
        *le32(CPU_TYPE_X86_64),
        *le32(CPU_SUBTYPE_LIB64 | CPU_SUBTYPE_I386_ALL),
        *le32(MH_EXECUTE),
        *le32(4),
        *le32(command_size),
        *le32(MH_NOUNDEFS),
        *le32(0)
    ]

    executable = bytes(head + zero + text + data_ + start) + binary
    result = executable + bytes([0] * (4096-len(executable)))  # Pad

    return result, program
