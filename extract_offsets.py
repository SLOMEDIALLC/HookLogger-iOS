#!/usr/bin/env python3
"""
iOS 26 / xnu-12377 - 直接从 GitHub 下载 XNU 源码，精确提取关键结构体偏移
策略：克隆 XNU，用 clang -cc1 -ast-dump json 解析结构体
"""
import subprocess, sys, os, re, json

XNU = 'xnu'

# ─── 写最小化 C 文件，只 include 关键内容 ───────────────────────────────────
# 我们从 XNU 头文件里手动抽取 proc/ucred/filedesc 的字段
# 先看完整 proc_internal.h 前 300 行
proc_h = open(f'{XNU}/bsd/sys/proc_internal.h').read()
ucred_h = open(f'{XNU}/bsd/sys/ucred.h').read()
filedesc_h = open(f'{XNU}/bsd/sys/filedesc.h').read()
task_h = open(f'{XNU}/osfmk/kern/task.h').read()
file_h = open(f'{XNU}/bsd/sys/file_internal.h').read() if os.path.exists(f'{XNU}/bsd/sys/file_internal.h') else ''

print("=== proc_internal.h (lines 1-150) ===")
lines = proc_h.split('\n')
for i, l in enumerate(lines[:150], 1):
    print(f"{i:4}: {l}")

print("\n=== task.h - bsd_info field ===")
for i, l in enumerate(task_h.split('\n'), 1):
    if 'bsd_info' in l or 'bsd_task_info' in l:
        print(f"{i:4}: {l}")

print("\n=== ucred.h (lines 1-100) ===")
ucred_lines = ucred_h.split('\n')
for i, l in enumerate(ucred_lines[:100], 1):
    print(f"{i:4}: {l}")

print("\n=== filedesc.h (lines 1-80) ===")
fd_lines = filedesc_h.split('\n')
for i, l in enumerate(fd_lines[:80], 1):
    print(f"{i:4}: {l}")

# 保存完整内容
with open('ios26_offsets.txt', 'w') as f:
    f.write("=== XNU-12377 struct analysis ===\n\n")
    f.write("--- proc_internal.h first 300 lines ---\n")
    f.write('\n'.join(lines[:300]))
    f.write("\n\n--- ucred.h first 150 lines ---\n")
    f.write('\n'.join(ucred_lines[:150]))
    f.write("\n\n--- filedesc.h first 150 lines ---\n")
    f.write('\n'.join(fd_lines[:150]))

print("\nSaved to ios26_offsets.txt")
