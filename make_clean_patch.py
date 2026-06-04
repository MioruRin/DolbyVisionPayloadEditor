#!/usr/bin/env python3
"""
Create a CLEAN patched EDID based on the ORIGINAL 778.bin file.
ONLY modify: byte 210 (9E -> 9F) + Block 1 checksum.
This preserves ALL VRR, refresh rates, and other data perfectly.
"""

import os

# Read original EDID
with open(r'C:\Users\MioruRin\Desktop\778.bin', 'rb') as f:
    original = f.read()

print(f"Original EDID: {len(original)} bytes")

# Make a copy
patched = bytearray(original)

# Modify ONLY byte 210: 0x9E -> 0x9F
print(f"Byte 210 before: 0x{patched[210]:02X}")
patched[210] = 0x9F
print(f"Byte 210 after:  0x{patched[210]:02X}")

# Recalculate Block 1 checksum (bytes 128-254, checksum at byte 255)
block1_sum = sum(patched[128:255])
new_cs = (0x100 - (block1_sum % 0x100)) % 0x100
print(f"Block 1 checksum: 0x{patched[255]:02X} -> 0x{new_cs:02X}")
patched[255] = new_cs

# Verify ALL checksums
for blk in range(3):
    start = blk * 128
    total = sum(patched[start:start+128])
    mod = total % 256
    cs = patched[start + 127]
    status = "OK" if mod == 0 else f"FAIL (mod={mod})"
    print(f"Block {blk} checksum: 0x{cs:02X} -> {status}")

# Count differences
diffs = [(i, patched[i], original[i]) for i in range(len(original)) if patched[i] != original[i]]
print(f"\nTotal bytes changed from original: {len(diffs)}")
for offset, b1, b2 in diffs:
    label = ""
    if offset == 210: label = " <-- DV target byte"
    elif offset == 255: label = " <-- Block 1 checksum (auto-fix)"
    print(f"  Byte {offset} (0x{offset:03X}): 0x{b2:02X} -> 0x{b1:02X}{label}")

# Save to Desktop
out_path = r'C:\Users\MioruRin\Desktop\XMI27B3_DV_clean.bin'
with open(out_path, 'wb') as f:
    f.write(patched)

print(f"\nSaved clean patched EDID: {out_path}")
print(f"  This file = original 778.bin + ONLY byte 210 (9E->9F) + Block 1 checksum")
print(f"  VRR, refresh rates, and all other data 100% PRESERVED")
