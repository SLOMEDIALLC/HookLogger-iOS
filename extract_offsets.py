#!/usr/bin/env python3
"""
iOS 26 / xnu-12377 kernel struct offset extractor
Runs on macOS with XNU source in ./xnu/
Uses clang -ast-dump to get struct layouts without full kernel compilation
"""
import subprocess, sys, os, re, json

XNU = 'xnu'

# 最小化 C 文件 —— 只包含我们需要的结构体定义
MINI_C = r"""
/* Minimal shim to get struct layouts from XNU headers */
#define KERNEL 1
#define KERNEL_PRIVATE 1
#define BSD_KERNEL_PRIVATE 1
#define XNU_KERNEL_PRIVATE 1
#define MACH_KERNEL_PRIVATE 1
#define __APPLE_API_PRIVATE 1
#define PRIVATE 1
#define MACH_ASSERT 0
#define MACH_LDEBUG 0
#define CONFIG_DTRACE 0
#define MONOTONIC 0
#define LOCK_STATS 0
#define CONFIG_PERVASIVE_COMPACTION 0
#define CONFIG_REQUIRES_U32_MSGID 0
#define DEBUG 0
#define DEVELOPMENT 0
#define CONFIG_THREAD_GROUPS 1
#define __arm64__ 1
#define __LP64__ 1

#include <stddef.h>
#include <stdint.h>

/* We only want sizeof/offsetof - fake what we can't include */
typedef unsigned int boolean_t;
typedef int kern_return_t;
typedef unsigned int natural_t;
typedef int integer_t;
typedef uint64_t mach_vm_address_t;
typedef uint64_t mach_vm_size_t;
typedef unsigned int mach_port_name_t;
typedef unsigned int mach_msg_type_number_t;
typedef unsigned long vm_size_t;
typedef unsigned long vm_offset_t;
typedef uint64_t vm_map_t;
typedef uint64_t ipc_port_t;
typedef void* lck_mtx_t;
typedef void* lck_rw_t;
typedef void* lck_spin_t;
typedef void* zone_t;
typedef int pid_t;
typedef unsigned int uid_t;
typedef unsigned int gid_t;
typedef unsigned short mode_t;
typedef long ssize_t;
typedef unsigned long size_t;
typedef long long off_t;
typedef unsigned int dev_t;
typedef unsigned long ino_t;
typedef unsigned long nlink_t;
typedef unsigned int u_int;
typedef unsigned short u_short;
typedef unsigned char u_char;
typedef unsigned long u_long;
typedef uint8_t u_int8_t;
typedef uint16_t u_int16_t;
typedef uint32_t u_int32_t;
typedef uint64_t u_int64_t;
typedef int32_t int32_t;
typedef uint32_t uint32_t;
typedef int64_t int64_t;

#include "bsd/sys/proc_internal.h"
#include "bsd/sys/ucred.h"

int main(void) { return 0; }
"""

out_file = f'{XNU}/mini_structs.c'
with open(out_file, 'w') as f:
    f.write(MINI_C)

# 用 clang -fdump-record-layouts 获取结构体布局
result = subprocess.run([
    'clang',
    '-target', 'arm64-apple-macos14.0',
    f'-I{XNU}',
    f'-I{XNU}/bsd',
    f'-I{XNU}/osfmk',
    f'-I{XNU}/libkern',
    f'-I{XNU}/EXTERNAL_HEADERS',
    '-DKERNEL=1', '-DKERNEL_PRIVATE=1', '-DBSD_KERNEL_PRIVATE=1',
    '-DXNU_KERNEL_PRIVATE=1', '-DMACH_KERNEL_PRIVATE=1',
    '-DPRIVATE=1', '-D__APPLE_API_PRIVATE=1',
    '-DMACH_ASSERT=0', '-DCONFIG_DTRACE=0',
    '-D__arm64__=1', '-D__LP64__=1',
    '-Wno-everything',
    '-fdump-record-layouts',
    '-fsyntax-only',
    out_file
], capture_output=True, text=True, timeout=120)

print("=== clang stderr (first 3000 chars) ===")
print(result.stderr[:3000])

if result.returncode != 0:
    print("FAILED - trying alternative approach...")

    # 备选：直接 grep XNU 头文件中的 offsetof 注释 / 已知常量
    print("\n=== Searching XNU headers for known offset constants ===")
    for pattern in [r'p_ucred', r'p_fd', r'bsd_info', r'fd_ofiles']:
        r2 = subprocess.run(['grep', '-rn', pattern, f'{XNU}/bsd', f'{XNU}/osfmk'],
                           capture_output=True, text=True)
        hits = [l for l in r2.stdout.split('\n') if pattern in l and 'define' in l.lower()]
        if hits:
            print(f"\n{pattern}:")
            for h in hits[:5]: print(f"  {h[:100]}")
else:
    print("Compile OK, layout dump below:")
    print(result.stdout[:5000])

# 尝试用 Python ctypes 方式
print("\n=== Alternative: Parse struct from header directly ===")
proc_h = f'{XNU}/bsd/sys/proc_internal.h'
if os.path.exists(proc_h):
    with open(proc_h) as f:
        content = f.read()
    # 找 struct proc { ... } 定义
    m = re.search(r'struct proc\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', content, re.DOTALL)
    if m:
        print("Found struct proc, first 500 chars:")
        print(m.group(1)[:500])

# 用 Python ast 解析 XNU 版本号
print("\n=== XNU Version Info ===")
version_f = f'{XNU}/makedefs/MakeInc.def'
if os.path.exists(version_f):
    with open(version_f) as f:
        for line in f:
            if 'VERSION' in line or 'KERNEL_VERSION' in line:
                print(f"  {line.strip()}")

with open('ios26_offsets.txt', 'w') as f:
    f.write("XNU-12377 offset extraction attempt\n")
    f.write(result.stderr[:5000])
    f.write(result.stdout[:5000])
print("\nSaved to ios26_offsets.txt")
