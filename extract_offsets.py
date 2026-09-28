#!/usr/bin/env python3
"""
iOS 26 / xnu-12377 - 确认 p_ucred 新位置 + 计算关键偏移
"""
import subprocess, sys, os, re

XNU = 'xnu'

proc_h    = open(f'{XNU}/bsd/sys/proc_internal.h').read()
proc_ro_h = open(f'{XNU}/bsd/sys/proc_ro.h').read() if os.path.exists(f'{XNU}/bsd/sys/proc_ro.h') else ''
ucred_h   = open(f'{XNU}/bsd/sys/ucred.h').read()
filedesc_h= open(f'{XNU}/bsd/sys/filedesc.h').read()
task_h    = open(f'{XNU}/osfmk/kern/task.h').read()

def find_struct_body(content, name):
    m = re.search(rf'\bstruct\s+{name}\s*\{{', content)
    if not m: return ''
    depth, i = 0, m.end()-1
    while i < len(content):
        if content[i]=='{': depth+=1
        elif content[i]=='}':
            depth-=1
            if depth==0: return content[m.start():i+1]
        i+=1
    return ''

print("=== proc_ro.h (full content) ===")
print(proc_ro_h[:6000])

print("\n=== struct task - first 200 lines ===")
for i,l in enumerate(task_h.split('\n')[:200], 1):
    print(f"{i:4}: {l}")

# 找 p_ucred 在哪
print("\n=== p_ucred in proc_internal.h ===")
for l in proc_h.split('\n'):
    if 'ucred' in l.lower():
        print(f"  {l.strip()[:100]}")

print("\n=== ucred in proc_ro.h ===")
for l in proc_ro_h.split('\n'):
    if 'ucred' in l.lower() or 'cred' in l.lower():
        print(f"  {l.strip()[:100]}")

print("\n=== bsd_info in task.h ===")
for l in task_h.split('\n'):
    if 'bsd_info' in l or 'bsd_task' in l:
        print(f"  {l.strip()[:100]}")

with open('ios26_offsets.txt', 'w') as f:
    f.write("=== proc_ro.h ===\n")
    f.write(proc_ro_h)
    f.write("\n\n=== task.h first 200 lines ===\n")
    f.write('\n'.join(task_h.split('\n')[:200]))
    f.write("\n\n=== p_ucred references ===\n")
    f.write('\n'.join(l for l in proc_h.split('\n') if 'ucred' in l.lower()))
    f.write("\n\n=== struct filedesc ===\n")
    f.write(find_struct_body(filedesc_h, 'filedesc'))

print("\nSaved ios26_offsets.txt")
