#!/usr/bin/env python3
"""
iOS 26 / xnu-12377 kernel struct offset extractor
"""
import subprocess, sys, os, re

XNU = 'xnu'

# 先创建缺失的 stub headers
stubs = {
    f'{XNU}/BUILD/obj/EXPORT_HDRS/mach_assert.h': '#pragma once\n',
    f'{XNU}/EXTERNAL_HEADERS/mach_assert.h': '#pragma once\n',
    f'{XNU}/osfmk/mach_assert.h': '#pragma once\n',
}
for path, content in stubs.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

# 极简 C 文件 - 让 XNU 自己 typedef，我们不重定义
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
#define CONFIG_XNUPOST 0
#define CONFIG_KCDATA_INIT 0

/* Let XNU define boolean_t as it wants */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "bsd/sys/proc_internal.h"
#include "bsd/sys/ucred.h"
#include "bsd/sys/filedesc.h"
#include "bsd/sys/file_internal.h"

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
    f'-I{XNU}/BUILD/obj/EXPORT_HDRS',
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

def parse_layout(dump, struct_name):
    offsets = {}
    in_struct = False
    struct_size = 0
    for line in dump.split('\n'):
        if f'*** Dumping AST Record Layout' in line and struct_name in line:
            in_struct = True
            continue
        if in_struct:
            if line.startswith('*** Dumping') or (line.strip() == '' and in_struct):
                in_struct = False
                continue
            # size line
            m_size = re.match(r'\s*sizeof=(\d+)', line)
            if m_size:
                struct_size = int(m_size.group(1))
                in_struct = False
                continue
            # field line: "   24 |   struct ucred * p_ucred"
            m = re.match(r'\s*(\d+)\s*\|\s*(?:[\w\s\*\[\]]+\s+)?(\w+)\s*$', line)
            if m:
                bit_off = int(m.group(1))
                field   = m.group(2)
                offsets[field] = bit_off // 8
    offsets['__sizeof__'] = struct_size
    return offsets

proc_fields  = parse_layout(dump, 'proc ')
ucred_fields = parse_layout(dump, 'ucred ')
fd_fields    = parse_layout(dump, 'filedesc ')

output_lines = [
    "=== iOS 26 / xnu-12377.121.6 Kernel Struct Offsets ===",
    "(arm64, compiled with clang -fdump-record-layouts)",
    ""
]

PROC_WANT  = ['p_list','p_pid','task','p_pgrp','p_fd','p_ucred','p_csflags','p_textvp','p_ppid']
UCRED_WANT = ['cr_ref','cr_uid','cr_svuid','cr_ruid','cr_rgid','cr_gid','cr_ngroups','cr_flags']
FD_WANT    = ['fd_ofiles','fd_nfiles','fd_lastfile','fd_cmask']

if proc_fields and len(proc_fields) > 1:
    output_lines.append("struct proc {")
    for f in PROC_WANT:
        if f in proc_fields:
            output_lines.append(f"    /* 0x{proc_fields[f]:03x} */ {f};")
    output_lines.append(f"}}; // sizeof = 0x{proc_fields.get('__sizeof__',0):x}")
    output_lines.append("")
else:
    output_lines.append("struct proc: NOT PARSED")
    output_lines.append("")

if ucred_fields and len(ucred_fields) > 1:
    output_lines.append("struct ucred {")
    for f in UCRED_WANT:
        if f in ucred_fields:
            output_lines.append(f"    /* 0x{ucred_fields[f]:03x} */ {f};")
    output_lines.append(f"}}; // sizeof = 0x{ucred_fields.get('__sizeof__',0):x}")
    output_lines.append("")

if fd_fields and len(fd_fields) > 1:
    output_lines.append("struct filedesc {")
    for f in FD_WANT:
        if f in fd_fields:
            output_lines.append(f"    /* 0x{fd_fields[f]:03x} */ {f};")
    output_lines.append(f"}}; // sizeof = 0x{fd_fields.get('__sizeof__',0):x}")
    output_lines.append("")

if not (proc_fields and len(proc_fields) > 1):
    output_lines.append("=== Compiler errors (first 4000 chars) ===")
    output_lines.append(result.stderr[:4000])

text = '\n'.join(output_lines)
print(text)
with open('ios26_offsets.txt', 'w') as f:
    f.write(text)
print("\nSaved ios26_offsets.txt")
