#!/usr/bin/env python3
"""
iOS 26 vs iOS 18 - 对比 proc_ro struct 是否有变化
确认 RO2RestrictedUcredPatcher 的 offset 是否还适用
"""
import urllib.request, os

def fetch(path, tag):
    url = f'https://raw.githubusercontent.com/apple-oss-distributions/xnu/{tag}/{path}'
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.read().decode(errors='replace')
    except Exception as e:
        return f'ERROR: {e}'

XNU = 'xnu'

# iOS 18 对应 xnu-11417.x
proc_ro_18 = open(f'{XNU}/bsd/sys/proc_ro.h').read() if os.path.exists(f'{XNU}/bsd/sys/proc_ro.h') else ''
proc_ro_26 = proc_ro_18  # already cloned xnu-12377

# 获取 iOS 18 的 proc_ro.h
print("Fetching iOS 18 (xnu-11417) proc_ro.h...")
proc_ro_18_content = fetch('bsd/sys/proc_ro.h', 'xnu-11417.101.15')
print("Fetching iOS 17 (xnu-11215) proc_ro.h...")
proc_ro_17_content = fetch('bsd/sys/proc_ro.h', 'xnu-11215.1.10')

print("=== proc_ro.h iOS 18 (xnu-11417) ===")
print(proc_ro_18_content[:3000])

print("\n=== proc_ro.h iOS 17 (xnu-11215) ===")
print(proc_ro_17_content[:2000])

print("\n=== proc_ro.h iOS 26 (xnu-12377) ===")
print(proc_ro_26[:3000])

# 检查 task.h 里的 bsd_info
print("\n\n=== task.h - searching bsd_info (iOS 26) ===")
task_h = open(f'{XNU}/osfmk/kern/task.h').read()
lines = task_h.split('\n')
# 找 struct task 定义
in_struct = False
for i, l in enumerate(lines):
    if 'struct task {' in l or 'struct task{' in l:
        in_struct = True
    if in_struct:
        print(f"{i+1:4}: {l}")
        if 'bsd_info' in l:
            print("       ^^^ bsd_info FOUND")
        if in_struct and i > 0 and l.strip() == '};' and in_struct:
            in_struct = False
            break
        if i > 400:
            break

# 用简单方法定位 task.bsd_info
print("\n=== All bsd_info refs in task.h ===")
for i, l in enumerate(lines):
    if 'bsd_info' in l:
        print(f"  line {i+1}: {l.strip()[:100]}")

result_lines = [
    "=== iOS 26 proc_ro structure ===",
    proc_ro_26,
    "\n\n=== iOS 18 proc_ro structure ===",
    proc_ro_18_content,
    "\n\n=== iOS 17 proc_ro structure ===",
    proc_ro_17_content,
    "\n\n=== task.h bsd_info references ===",
    '\n'.join(f"line {i+1}: {l}" for i, l in enumerate(task_h.split('\n')) if 'bsd_info' in l),
]
with open('ios26_offsets.txt', 'w') as f:
    f.write('\n'.join(result_lines))
print("\nSaved ios26_offsets.txt")
