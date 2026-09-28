#!/usr/bin/env python3
"""
iOS 26 / xnu-12377 kernel struct offset extractor
Approach: Read XNU headers from GitHub, parse struct layouts with Python
ARM64 ABI: pointers=8B, uint32=4B, uint64=8B, int=4B
"""
import urllib.request, json, re, sys

BASE = 'https://raw.githubusercontent.com/apple-oss-distributions/xnu/xnu-12377.121.6'
COMP = 'https://raw.githubusercontent.com/apple-oss-distributions/xnu/xnu-10002.81.5'  # iOS 15

def fetch(path, tag='xnu-12377.121.6'):
    url = f'https://raw.githubusercontent.com/apple-oss-distributions/xnu/{tag}/{path}'
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.read().decode(errors='replace')
    except:
        return ''

# ARM64 type sizes/alignments
TYPE_INFO = {
    'int': (4, 4), 'unsigned int': (4, 4), 'uint32_t': (4, 4), 'u_int32_t': (4, 4),
    'long': (8, 8), 'unsigned long': (8, 8),
    'uint64_t': (8, 8), 'u_int64_t': (8, 8), 'int64_t': (8, 8),
    'uint16_t': (2, 2), 'u_int16_t': (2, 2), 'int16_t': (2, 2),
    'uint8_t': (1, 1), 'u_int8_t': (1, 1), 'int8_t': (1, 1), 'char': (1, 1),
    'bool': (1, 1), 'boolean_t': (4, 4),
    'pid_t': (4, 4), 'uid_t': (4, 4), 'gid_t': (4, 4), 'mode_t': (2, 2),
    'short': (2, 2), 'unsigned short': (2, 2),
    'size_t': (8, 8), 'ssize_t': (8, 8), 'off_t': (8, 8),
    # Pointers / pointer-sized
    'pointer': (8, 8),
}

def align_up(val, align):
    return (val + align - 1) & ~(align - 1)

def parse_struct_simple(struct_def):
    """
    Simplified struct layout: look for patterns like
      field_type field_name;
    Handles pointers (*) and arrays ([N])
    Returns dict {field_name: byte_offset}
    """
    offsets = {}
    offset = 0

    # Remove comments
    struct_def = re.sub(r'/\*.*?\*/', '', struct_def, flags=re.DOTALL)
    struct_def = re.sub(r'//.*$', '', struct_def, flags=re.MULTILINE)

    # Parse each field
    for line in struct_def.split(';'):
        line = line.strip()
        if not line or '{' in line or '}' in line or '#' in line:
            continue

        # Check for pointer
        is_ptr = '*' in line
        # Check for array
        arr_m = re.search(r'\[(\d+)\]', line)
        arr_count = int(arr_m.group(1)) if arr_m else 1

        # Extract field name (last word before optional [])
        name_m = re.search(r'(\w+)\s*(?:\[\d+\])?\s*$', line)
        if not name_m:
            continue
        field_name = name_m.group(1)

        if is_ptr:
            sz, align = 8, 8
        else:
            # Find type
            sz, align = 4, 4  # default
            for tname, (tsz, talign) in TYPE_INFO.items():
                if tname in line:
                    sz, align = tsz, talign
                    break

        offset = align_up(offset, align)
        offsets[field_name] = offset
        offset += sz * arr_count

    return offsets, offset

# ─── Fetch and parse proc_internal.h ───────────────────────────────────────
print("Fetching XNU headers from GitHub...")
proc_h = fetch('bsd/sys/proc_internal.h')
ucred_h = fetch('bsd/sys/ucred.h')
filedesc_h = fetch('bsd/sys/filedesc.h')
file_h = fetch('bsd/sys/file_internal.h')
task_h = fetch('osfmk/kern/task.h')

print(f"proc_internal.h: {len(proc_h)} chars")
print(f"ucred.h: {len(ucred_h)} chars")
print(f"filedesc.h: {len(filedesc_h)} chars")

# Extract struct proc body
def extract_struct(content, name):
    # Find "struct name {" ... "}"
    pattern = rf'struct\s+{name}\s*\{{([^}}]{{0,20000}})\}}'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        return m.group(1)
    # Try with typedef
    pattern2 = rf'typedef\s+struct\s+{name}\s*\{{([^}}]{{0,20000}})\}}'
    m2 = re.search(pattern2, content, re.DOTALL)
    if m2:
        return m2.group(1)
    return ''

proc_body    = extract_struct(proc_h, 'proc')
ucred_body   = extract_struct(ucred_h, 'ucred')
filedesc_body= extract_struct(filedesc_h, 'filedesc')

# Show key proc fields
print("\n=== struct proc fields (first 50 lines) ===")
if proc_body:
    for i, line in enumerate(proc_body.split('\n')[:50]):
        print(f"  {line}")

# Look for key fields directly with grep
print("\n=== Key field locations in proc_internal.h ===")
for field in ['p_ucred', 'p_fd', 'p_pid', 'p_csflags', 'task']:
    hits = [l.strip() for l in proc_h.split('\n') if field in l and ';' in l][:3]
    for h in hits:
        print(f"  {field}: {h[:80]}")

print("\n=== Key field locations in ucred.h ===")
for field in ['cr_uid', 'cr_svuid', 'cr_rgid', 'cr_gid']:
    hits = [l.strip() for l in ucred_h.split('\n') if field in l and ';' in l][:2]
    for h in hits:
        print(f"  {field}: {h[:80]}")

# ─── Compare with iOS 15 to find delta ─────────────────────────────────────
print("\n=== Comparing xnu-12377 vs xnu-10002 (iOS 15) ===")
proc_h_15 = fetch('bsd/sys/proc_internal.h', 'xnu-10002.81.5')
proc_body_15 = extract_struct(proc_h_15, 'proc')
print(f"proc body iOS26: {len(proc_body)} chars")
print(f"proc body iOS15: {len(proc_body_15)} chars")

# Count fields before p_ucred in each version
def count_before(body, field):
    lines = [l.strip() for l in body.split(';') if l.strip() and ';' not in l[:-1]]
    count = 0
    for l in lines:
        if field in l:
            break
        if re.search(r'\w+\s*\**\s*\w+\s*(\[\d+\])?$', l):
            count += 1
    return count

if proc_body:
    with open('ios26_offsets.txt', 'w') as f:
        f.write("=== iOS 26 / xnu-12377 proc struct fields ===\n")
        f.write(proc_body[:3000])
        f.write("\n\n=== ucred struct fields ===\n")
        f.write(ucred_body[:1000])
        f.write("\n\n=== filedesc struct fields ===\n")
        f.write(filedesc_body[:1000])
    print("\nSaved struct definitions to ios26_offsets.txt")
else:
    with open('ios26_offsets.txt', 'w') as f:
        f.write("Failed to parse - proc header first 2000 chars:\n")
        f.write(proc_h[:2000])
    print("Failed to parse struct")
