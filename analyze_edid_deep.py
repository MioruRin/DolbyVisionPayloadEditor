#!/usr/bin/env python3
"""Deep analysis: why AWE rewrote the entire EDID block"""

f1_path = r'C:\Users\MioruRin\Downloads\1 (1).bin'  # AWE modified
f2_path = r'C:\Users\MioruRin\Desktop\778.bin'       # Original

with open(f1_path, 'rb') as f:
    d1 = f.read()
with open(f2_path, 'rb') as f:
    d2 = f.read()

print("=" * 80)
print("DEEP EDID ANALYSIS: AWE modified vs Original")
print("=" * 80)

# === Block 0 (Base EDID, bytes 0-127) ===
print("\n### BLOCK 0 (Base EDID, bytes 0-127) ###")
print(f"  File1 length: {len(d1)}, File2 length: {len(d2)}")

# Header
print(f"\n  Header: {'MATCH' if d1[:8] == d2[:8] else 'DIFF'} ({d1[:8].hex()} vs {d2[:8].hex()})")
# Manufacturer ID (bytes 8-9)
print(f"  Manufacturer: {'MATCH' if d1[8:10] == d2[8:10] else 'DIFF'}")
# Product code (bytes 10-11)
print(f"  Product code: {'MATCH' if d1[10:12] == d2[10:12] else 'DIFF'}")
# Serial (bytes 12-15)
print(f"  Serial: {'MATCH' if d1[12:16] == d2[12:16] else 'DIFF'}")
# Week/Year (bytes 16-17)
print(f"  Week/Year: {'MATCH' if d1[16:18] == d2[16:18] else 'DIFF'}")
# EDID version (bytes 18-19)
print(f"  EDID version: {'MATCH' if d1[18:20] == d2[18:20] else 'DIFF'} ({d1[18]}.{d1[19]} vs {d2[18]}.{d2[19]})")

# Display parameters (bytes 20-24)
print(f"\n  Display params (20-24): {'MATCH' if d1[20:25] == d2[20:25] else 'DIFF'}")
if d1[20:25] != d2[20:25]:
    print(f"    File1: {d1[20:25].hex()}")
    print(f"    File2: {d2[20:25].hex()}")

# Chromaticity (bytes 25-34)
print(f"  Chromaticity (25-34): {'MATCH' if d1[25:35] == d2[25:35] else 'DIFF'}")

# Established timings (bytes 35-37)
print(f"  Established timings (35-37): {'MATCH' if d1[35:38] == d2[35:38] else 'DIFF'}")

# Standard timings (bytes 38-53)
print(f"  Standard timings (38-53): {'MATCH' if d1[38:54] == d2[38:54] else 'DIFF'}")
if d1[38:54] != d2[38:54]:
    print(f"    File1: {d1[38:54].hex()}")
    print(f"    File2: {d2[38:54].hex()}")

# Descriptor 1 (bytes 54-71)
print(f"  Descriptor 1 (54-71): {'MATCH' if d1[54:72] == d2[54:72] else 'DIFF'}")
# Descriptor 2 (bytes 72-89)
print(f"  Descriptor 2 (72-89): {'MATCH' if d1[72:90] == d2[72:90] else 'DIFF'}")
# Descriptor 3 (bytes 90-107)
print(f"  Descriptor 3 (90-107): {'MATCH' if d1[90:108] == d2[90:108] else 'DIFF'}")
# Descriptor 4 (bytes 108-125)
print(f"  Descriptor 4 (108-125): {'MATCH' if d1[108:126] == d2[108:126] else 'DIFF'}")
# Extensions count (byte 126)
print(f"  Extension count (byte 126): File1={d1[126]} vs File2={d2[126]}")
# Checksum (byte 127)
print(f"  Block 0 checksum (byte 127): 0x{d1[127]:02X} vs 0x{d2[127]:02X}")

# Count block 0 diffs
b0_diffs = [(i, d1[i], d2[i]) for i in range(128) if d1[i] != d2[i]]
print(f"\n  Block 0 total diff bytes: {len(b0_diffs)}")
for offset, b1, b2 in b0_diffs:
    print(f"    Byte {offset} (0x{offset:02X}): 0x{b1:02X} -> 0x{b2:02X}")

# === Block 1 (CTA-861 Extension, bytes 128-255) ===
print("\n\n### BLOCK 1 (CTA-861 Extension, bytes 128-255) ###")
print(f"  Tag (byte 128): File1=0x{d1[128]:02X} vs File2=0x{d1[128]:02X}")
print(f"  Revision (byte 129): File1={d1[129]} vs File2={d2[129]}")
print(f"  Byte 130 (DTD offset start): File1={d1[130]} (0x{d1[130]:02X}) vs File2={d2[130]} (0x{d2[130]:02X})")
print(f"  Byte 131: File1={d1[131]} (0x{d1[131]:02X}) vs File2={d2[131]} (0x{d2[131]:02X})")

# Native DTD count
print(f"\n  CTA-861 header bytes 128-131: {'MATCH' if d1[128:132] == d2[128:132] else 'DIFF'}")
if d1[128:132] != d2[128:132]:
    print(f"    File1: {d1[128:132].hex()}")
    print(f"    File2: {d2[128:132].hex()}")

# Find DV VSDB in both files
def find_dv_vsdb(data):
    """Find Dolby Vision VSDB (OUI 00D046) in data"""
    oui_bytes = bytes([0x46, 0xD0, 0x00])  # little-endian 0x00D046
    results = []
    for i in range(len(data) - 3):
        if data[i:i+3] == oui_bytes:
            results.append(i)
    return results

dv1 = find_dv_vsdb(d1)
dv2 = find_dv_vsdb(d2)
print(f"\n  Dolby VSDB (OUI 00D046):")
print(f"    File1 found at byte: {dv1}")
print(f"    File2 found at byte: {dv2}")

# Show DV VSDB region in both
for fname, data, positions in [("File1 (AWE)", d1, dv1), ("File2 (Orig)", d2, dv2)]:
    for pos in positions:
        print(f"\n  {fname} DV VSDB at byte {pos}:")
        start = max(0, pos - 4)
        end = min(len(data), pos + 20)
        for i in range(start, end):
            marker = " <-- OUI start" if i == pos else ""
            marker2 = " <-- Payload start" if i == pos + 3 else ""
            marker3 = " <-- Target byte" if i == pos + 3 + 2 else ""
            print(f"    [{i}] 0x{data[i]:02X}{marker}{marker2}{marker3}")

# Detailed tag/length analysis for CTA-861 extension
print("\n\n### CTA-861 Extension Data Block Analysis ###")

def parse_cta_blocks(data, block_start, block_name):
    """Parse CTA-861 data blocks (tags 0x02-0xFF)"""
    print(f"\n  --- {block_name} ---")
    offset = 132  # after header
    block_end = block_start + 127
    count = 0
    while offset < block_end:
        tag_byte = data[offset]
        if tag_byte == 0x00:  # padding
            offset += 1
            continue
        if tag_byte == 0x01:  # audio block
            length = data[offset + 1]
            tag_name = "Audio Data Block"
        elif tag_byte == 0x02:  # vendor specific
            length = data[offset + 1]
            tag_name = "Vendor Specific Data Block"
        elif tag_byte == 0x03:  # speaker alloc
            length = data[offset + 1]
            tag_name = "Speaker Allocation Data Block"
        elif tag_byte == 0x04:  # video capabilities
            length = 3
            tag_name = "Video Capabilities Data Block"
        elif tag_byte == 0x10:  # HDMI VSDB
            length = data[offset + 1]
            tag_name = "HDMI Vendor Specific Data Block"
        elif tag_byte == 0x20:  # YCbCr 4:2:0
            length = data[offset + 1]
            tag_name = "YCbCr 4:2:0 Capability Map"
        elif tag_byte == 0x30:  # YCbCr 4:4:4
            length = data[offset + 1]
            tag_name = "YCbCr 4:4:4 Capability Map"
        elif tag_byte == 0x40:  # Video format preference
            length = data[offset + 1]
            tag_name = "Video Format Preference"
        elif tag_byte == 0x50:  # HDR static metadata
            length = data[offset + 1]
            tag_name = "HDR Static Metadata Data Block"
        elif tag_byte == 0x60:  # HDR dynamic metadata
            length = data[offset + 1]
            tag_name = "HDR Dynamic Metadata Data Block"
        elif tag_byte == 0x70:  # Extended tag
            ext_tag = data[offset + 2]
            length = data[offset + 1]
            tag_name = f"Extended Tag Block (0x{ext_tag:02X})"
        elif tag_byte >= 0x07 and tag_byte <= 0x0F:
            length = data[offset + 1]
            tag_name = f"Reserved Block (0x{tag_byte:02X})"
        else:
            length = data[offset + 1]
            tag_name = f"Unknown Block (0x{tag_byte:02X})"

        content = data[offset:offset+2+length]
        print(f"    Offset {offset}: Tag=0x{tag_byte:02X} [{tag_name}], Length={length}")
        print(f"      Data: {content.hex()}")

        offset += 2 + length
        count += 1
        if count > 20:
            print("    ... (truncated)")
            break
    # Show remaining bytes
    if offset < block_end:
        print(f"    Remaining bytes {offset}-{block_end-1}: {data[offset:block_end].hex()}")

parse_cta_blocks(d1, 128, "File1 (AWE modified)")
parse_cta_blocks(d2, 128, "File2 (Original)")

# VRR / refresh rate related
print("\n\n### VRR & Refresh Rate Analysis ###")

# Check for DisplayID or VRR-related data in both
# VRR in CTA-861 can be in Video Capabilities (tag 0x04)
# Also check if there's a second extension block

ext1_tag = d1[128]
ext2_start = None
if len(d1) > 256:
    ext2_tag = d1[256]
    print(f"  File1: Extension block 2 exists, tag=0x{ext2_tag:02X}")
    ext2_start = 256
else:
    print(f"  File1: No extension block 2")

if len(d2) > 256:
    ext2_tag = d2[256]
    print(f"  File2: Extension block 2 exists, tag=0x{ext2_tag:02X}")
else:
    print(f"  File2: No extension block 2")

# Check for "6F" byte in DV region
print(f"\n  DV VSDB tail bytes:")
if dv1:
    for pos in dv1:
        print(f"    File1 @byte {pos}: bytes {pos+3} to {pos+12}: {d1[pos+3:pos+13].hex()}")
if dv2:
    for pos in dv2:
        print(f"    File2 @byte {pos}: bytes {pos+3} to {pos+12}: {d2[pos+3:pos+13].hex()}")

# === Block-by-block diff summary ===
print("\n\n### BLOCK-BY-BLOCK DIFF COUNT ###")
for blk in range(3):
    start = blk * 128
    end = start + 128
    diffs = [(i, d1[i], d2[i]) for i in range(start, end) if d1[i] != d2[i]]
    print(f"  Block {blk} (bytes {start}-{end-1}): {len(diffs)} diff bytes")

print("\n\n### CONCLUSION ###")
print(f"  Total bytes different: {sum(1 for i in range(max(len(d1),len(d2))) if (d1[i] if i<len(d1) else None) != (d2[i] if i<len(d2) else None))}")
print(f"  Total identical bytes: {min(len(d1),len(d2)) - sum(1 for i in range(min(len(d1),len(d2))) if d1[i] != d2[i])}")
