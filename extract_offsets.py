#!/usr/bin/env python3
"""
iOS 26 / xnu-12377 - 精确计算 struct proc/ucred/filedesc 偏移
用 pycparser 或手动计算
"""
import subprocess, sys, os, re

XNU = 'xnu'

# pip install pycparser
subprocess.run([sys.executable, '-m', 'pip', 'install', 'pycparser', '-q'], check=False)

proc_h = open(f'{XNU}/bsd/sys/proc_internal.h').read()
proc_ro_h = open(f'{XNU}/bsd/sys/proc_ro.h').read() if os.path.exists(f'{XNU}/bsd/sys/proc_ro.h') else ''
ucred_h = open(f'{XNU}/bsd/sys/ucred.h').read()
filedesc_h = open(f'{XNU}/bsd/sys/filedesc.h').read()
task_h = open(f'{XNU}/osfmk/kern/task.h').read()

# 找 struct proc 定义起点
def find_struct(content, name):
    """找 struct NAME { ... } 的完整定义"""
    # 找 struct proc {
    pattern = rf'\bstruct\s+{name}\s*\{{'
    m = re.search(pattern, content)
    if not m:
        return '', 0
    start = m.start()
    # 找配对的 }
    depth = 0
    i = m.end() - 1  # 从 { 开始
    while i < len(content):
        if content[i] == '{': depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                return content[start:i+1], start
        i += 1
    return '', 0

# 输出 struct proc 完整定义
struct_proc, _ = find_struct(proc_h, 'proc')
struct_proc_ro, _ = find_struct(proc_ro_h, 'proc_ro')
struct_ucred, _ = find_struct(ucred_h, 'ucred')
struct_fd, _ = find_struct(filedesc_h, 'filedesc')
struct_task, _ = find_struct(task_h, 'task')

print("=== struct proc (xnu-12377) ===")
print(struct_proc[:5000] if struct_proc else "NOT FOUND")

print("\n=== struct ucred (xnu-12377) ===")
print(struct_ucred[:2000] if struct_ucred else "NOT FOUND")

print("\n=== struct filedesc (xnu-12377) ===")
print(struct_fd[:2000] if struct_fd else "NOT FOUND")

print("\n=== task.h - bsd_info ===")
for l in task_h.split('\n'):
    if 'bsd_info' in l or 'bsd_task' in l:
        print(f"  {l.strip()[:100]}")

result = '\n'.join([
    "=== struct proc ===", struct_proc,
    "\n=== struct proc_ro ===", struct_proc_ro[:2000],
    "\n=== struct ucred ===", struct_ucred,
    "\n=== struct filedesc ===", struct_fd,
    "\n=== task bsd_info ===",
    '\n'.join(l for l in task_h.split('\n') if 'bsd_info' in l or 'bsd_task' in l),
])

with open('ios26_offsets.txt', 'w') as f:
    f.write(result)
print("\nSaved ios26_offsets.txt")
