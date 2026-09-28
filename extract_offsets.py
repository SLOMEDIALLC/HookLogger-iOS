import subprocess, sys

XNU = 'xnu'

PROG = """
#define KERNEL 1
#define KERNEL_PRIVATE 1
#define BSD_KERNEL_PRIVATE 1
#define XNU_KERNEL_PRIVATE 1
#define MACH_KERNEL_PRIVATE 1
#define __APPLE_API_PRIVATE 1
#define PRIVATE 1
#define MACH_ASSERT 0

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include "bsd/sys/proc_internal.h"
#include "bsd/sys/ucred.h"
#include "bsd/sys/filedesc.h"
#include "bsd/sys/file_internal.h"
#include "osfmk/kern/task.h"

int main(void) {
    printf("=== iOS 26 / xnu-12377 Kernel Offsets ===\\n");
    printf("PROC_P_UCRED       = 0x%zx\\n", __builtin_offsetof(struct proc, p_ucred));
    printf("PROC_P_FD          = 0x%zx\\n", __builtin_offsetof(struct proc, p_fd));
    printf("PROC_P_PID         = 0x%zx\\n", __builtin_offsetof(struct proc, p_pid));
    printf("PROC_P_CSFLAGS     = 0x%zx\\n", __builtin_offsetof(struct proc, p_csflags));
    printf("PROC_STRUCT_SIZE   = 0x%zx\\n", sizeof(struct proc));
    printf("TASK_BSD_INFO      = 0x%zx\\n", __builtin_offsetof(struct task, bsd_info));
    printf("UCRED_CR_UID       = 0x%zx\\n", __builtin_offsetof(struct ucred, cr_uid));
    printf("UCRED_CR_SVUID     = 0x%zx\\n", __builtin_offsetof(struct ucred, cr_svuid));
    printf("UCRED_CR_RGID      = 0x%zx\\n", __builtin_offsetof(struct ucred, cr_rgid));
    printf("FILEDESC_FD_OFILES = 0x%zx\\n", __builtin_offsetof(struct filedesc, fd_ofiles));
    return 0;
}
"""

with open(f'{XNU}/get_offsets.c', 'w') as f:
    f.write(PROG)

r = subprocess.run([
    'clang',
    '-target', 'arm64-apple-macos15.0',
    f'-I{XNU}', f'-I{XNU}/bsd', f'-I{XNU}/osfmk',
    f'-I{XNU}/libkern', f'-I{XNU}/EXTERNAL_HEADERS',
    '-DKERNEL=1', '-DKERNEL_PRIVATE=1', '-DBSD_KERNEL_PRIVATE=1',
    '-DXNU_KERNEL_PRIVATE=1', '-DMACH_KERNEL_PRIVATE=1',
    '-DPRIVATE=1', '-D__APPLE_API_PRIVATE=1',
    '-Wno-everything',
    '-o', f'{XNU}/get_offsets',
    f'{XNU}/get_offsets.c',
], capture_output=True, text=True)

if r.returncode != 0:
    print("COMPILE ERROR:")
    print(r.stderr[:5000])
    sys.exit(1)

run = subprocess.run([f'./{XNU}/get_offsets'], capture_output=True, text=True)
output = run.stdout
print(output)

with open('ios26_offsets.txt', 'w') as f:
    f.write(output)
print("Saved to ios26_offsets.txt")
