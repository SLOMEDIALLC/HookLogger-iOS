#!/usr/bin/env python3
"""
iOS 26 / xnu-12377 kernel struct offset extractor
Uses clang -Xclang -fdump-record-layouts to get struct layouts
"""
import subprocess, sys, os, re

XNU = 'xnu'

MINI_C = r"""
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
#define __arm64__ 1
#define __LP64__ 1
#define ARM_PGSHIFT 14
#define CONFIG_THREAD_GROUPS 1
#define CONFIG_PERVASIVE_COMPACTION 0
#define CONFIG_REQUIRES_U32_MSGID 0

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

/* Forward declarations to satisfy missing types */
typedef unsigned int boolean_t;
typedef int kern_return_t;
typedef unsigned int natural_t;
typedef uint64_t mach_vm_address_t;
typedef uint64_t mach_vm_size_t;
typedef unsigned int mach_port_name_t;
typedef unsigned long vm_size_t;
typedef uint64_t vm_map_t;
typedef uint64_t ipc_port_t;
typedef int pid_t;
typedef unsigned int uid_t;
typedef unsigned int gid_t;
typedef unsigned short mode_t;
typedef unsigned long size_t;
typedef long long off_t;
typedef unsigned int dev_t;
typedef unsigned long ino_t;
typedef uint8_t u_int8_t;
typedef uint16_t u_int16_t;
typedef uint32_t u_int32_t;
typedef uint64_t u_int64_t;
typedef unsigned int u_int;
typedef unsigned short u_short;
typedef unsigned char u_char;
typedef unsigned long u_long;

#include "bsd/sys/proc_internal.h"
#include "bsd/sys/ucred.h"
#include "bsd/sys/filedesc.h"

void dummy(void) {
    (void)sizeof(struct proc);
    (void)sizeof(struct ucred);
    (void)sizeof(struct filedesc);
}
"""

with open(f'{XNU}/mini.c', 'w') as f:
    f.write(MINI_C)

CFLAGS = [
    'clang',
    '-target', 'arm64-apple-macos14.0',
    f'-I{XNU}', f'-I{XNU}/bsd', f'-I{XNU}/osfmk',
    f'-I{XNU}/libkern', f'-I{XNU}/EXTERNAL_HEADERS',
    '-DKERNEL=1', '-DKERNEL_PRIVATE=1', '-DBSD_KERNEL_PRIVATE=1',
    '-DXNU_KERNEL_PRIVATE=1', '-DMACH_KERNEL_PRIVATE=1',
    '-DPRIVATE=1', '-D__APPLE_API_PRIVATE=1',
    '-DMACH_ASSERT=0', '-DCONFIG_DTRACE=0', '-D__arm64__=1', '-D__LP64__=1',
    '-Wno-everything',
    '-Xclang', '-fdump-record-layouts',
    '-fsyntax-only',
    f'{XNU}/mini.c'
]

result = subprocess.run(CFLAGS, capture_output=True, text=True, timeout=120)
dump = result.stderr + result.stdout

# 解析 layout dump 里的偏移
results = {}

def parse_layout(dump, struct_name):
    """从 clang record layout dump 中提取字段偏移（bit/8 = byte）"""
    offsets = {}
    in_struct = False
    for line in dump.split('\n'):
        if f'*** Dumping AST Record Layout' in line and struct_name in line:
            in_struct = True
            continue
        if in_struct:
            if line.strip() == '':
                in_struct = False
                continue
            # 格式: "  offset |   type field"
            # 或:   "      24 |   struct proc * p_ucred"
            m = re.match(r'\s*(\d+)\s*\|\s*\S+\s+(\w+)', line)
            if m:
                bit_off = int(m.group(1))
                field   = m.group(2)
                offsets[field] = bit_off // 8
    return offsets

proc_fields  = parse_layout(dump, 'proc')
ucred_fields = parse_layout(dump, 'ucred')
fd_fields    = parse_layout(dump, 'filedesc')

output = ["=== iOS 26 / xnu-12377 Kernel Struct Offsets ===",
          f"(arm64, from XNU-12377.121.6 source)",
          ""]

if proc_fields:
    output.append("struct proc:")
    for f in ['p_list', 'p_pid', 'task', 'p_pgrp', 'p_fd', 'p_ucred', 'p_csflags', 'p_textvp']:
        if f in proc_fields:
            output.append(f"  offsetof(proc, {f:20}) = 0x{proc_fields[f]:03x}")
    output.append(f"  sizeof(proc)                    = 0x{proc_fields.get('_END_',0):03x}")
    output.append("")

if ucred_fields:
    output.append("struct ucred:")
    for f in ['cr_ref', 'cr_uid', 'cr_svuid', 'cr_ruid', 'cr_rgid', 'cr_gid', 'cr_ngroups']:
        if f in ucred_fields:
            output.append(f"  offsetof(ucred, {f:20}) = 0x{ucred_fields[f]:03x}")
    output.append("")

if fd_fields:
    output.append("struct filedesc:")
    for f in ['fd_ofiles', 'fd_nfiles', 'fd_lastfile']:
        if f in fd_fields:
            output.append(f"  offsetof(filedesc, {f:20}) = 0x{fd_fields[f]:03x}")
    output.append("")

if not proc_fields and not ucred_fields:
    output.append("WARNING: No layout data parsed. Compiler stderr:")
    output.append(result.stderr[:3000])

text = '\n'.join(output)
print(text)
with open('ios26_offsets.txt', 'w') as f:
    f.write(text)
print("\nSaved ios26_offsets.txt")
