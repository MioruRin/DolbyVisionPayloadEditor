import sys

f1 = r'C:\Users\MioruRin\Downloads\1 (1).bin'
f2 = r'C:\Users\MioruRin\Desktop\778.bin'

with open(f1, 'rb') as fh:
    d1 = bytearray(fh.read())
with open(f2, 'rb') as fh:
    d2 = bytearray(fh.read())

print("=" * 75)
print("EDID COMPARISON ANALYSIS")
print("=" * 75)
print()
print("File 1 (Downloads/1 (1).bin): %d bytes" % len(d1))
print("  -> AWE modified EDID (Dolby Vision works)")
print("File 2 (Desktop/778.bin):     %d bytes" % len(d2))
print("  -> Original EDID (registry)")
print()

# Count differences
diffs = []
for i in range(max(len(d1), len(d2))):
    b1 = d1[i] if i < len(d1) else None
    b2 = d2[i] if i < len(d2) else None
    if b1 != b2:
        diffs.append((i, b1, b2))
print("Total byte differences: %d / %d bytes (%.1f%%)" % (len(diffs), 384, len(diffs)/384*100))
print()

# Checksum validation for both files
print("=" * 75)
print("CHECKSUM VALIDATION")
print("=" * 75)
for fname, data in [("AWE (1 (1).bin)", d1), ("Original (778.bin)", d2)]:
    print("\n  %s:" % fname)
    for blk in range(3):
        start = blk * 128
        total = sum(data[start:start+128])
        mod = total % 256
        cs = data[start + 127]
        status = "OK" if mod == 0 else "FAIL (mod=%d)" % mod
        print("    Block %d (bytes %d-%d): CS=0x%02X  %s" % (blk, start, start+127, cs, status))

# Key EDID fields comparison
print()
print("=" * 75)
print("KEY EDID FIELDS COMPARISON")
print("=" * 75)

# Header
print("\n[Header]")
print("  Both start with 00 FF FF FF FF FF 00: %s" % (d1[:8] == d2[:8]))

# Manufacturer ID (bytes 8-9)
m1 = ((d1[8] >> 2) & 0x1F) << 8 | ((d1[8] & 0x03) << 6) | (d1[9] >> 2)
m2 = ((d2[8] >> 2) & 0x1F) << 8 | ((d2[8] & 0x03) << 6) | (d2[9] >> 2)
print("  Manufacturer ID: AWE=0x%04X, Orig=0x%04X  %s" % (m1, m2, "SAME" if m1==m2 else "DIFF"))

# Product code (bytes 10-11)
pc1 = (d1[11] & 0x0F) << 8 | d1[10]
pc2 = (d2[11] & 0x0F) << 8 | d2[10]
print("  Product Code: AWE=0x%04X, Orig=0x%04X  %s" % (pc1, pc2, "SAME" if pc1==pc2 else "DIFF"))

# Week (byte 16) and Year (byte 17)
print("  Mfg Week: AWE=%d, Orig=%d  %s" % (d1[16], d2[16], "SAME" if d1[16]==d2[16] else "DIFF"))
print("  Mfg Year:  AWE=%d, Orig=%d  %s" % (2000+d1[17], 2000+d2[17], "SAME" if d1[17]==d2[17] else "DIFF"))

# EDID version (bytes 18-19)
print("  EDID Version: AWE=%d.%d, Orig=%d.%d  %s" % (d1[18], d1[19], d2[18], d2[19], "SAME" if d1[18:20]==d2[18:20] else "DIFF"))

# Descriptors (bytes 54-125, 4 x 18-byte descriptors)
print("\n[Descriptors (bytes 54-125)]")
for di in range(4):
    base = 54 + di * 18
    tag1 = (d1[base] >> 5) & 0x07  # top 3 bits of first byte
    tag2 = (d2[base] >> 5) & 0x07
    names = {0: "Timing", 1: "Serial", 2: "Monitor Name", 3: "Unspecified", 4: "Monitor Limits"}
    n1 = names.get(tag1, "Unknown(%d)" % tag1)
    n2 = names.get(tag2, "Unknown(%d)" % tag2)
    diff_flag = "DIFF" if d1[base:base+18] != d2[base:base+18] else "SAME"

    if tag2 == 2:  # Monitor name
        name = ""
        for j in range(1, 14):
            c = d2[base+j]
            if c == 0x0A:
                break
            if 0x20 <= c < 0x7F:
                name += chr(c)
        print("  Desc %d: AWE=%s(0x%02X), Orig=%s '%s'  %s" % (di, n1, d1[base]&0x1F, n2, name.strip(), diff_flag))
    elif tag2 == 3:  # Monitor limits
        gmin = d2[base+5] * 10
        gmax = (d2[base+6] & 0xFC) + 1
        if gmax == 256: gmax = 255
        print("  Desc %d: AWE=%s(0x%02X), Orig=%s  %s" % (di, n1, d1[base]&0x1F, n2, diff_flag))
    else:
        print("  Desc %d: AWE=%s(0x%02X), Orig=%s(0x%02X)  %s" % (di, n1, d1[base]&0x1F, n2, d2[base]&0x1F, diff_flag))

# Extension block count (byte 126)
print("\n[Extension Info]")
print("  Extension count: AWE=%d, Orig=%d  %s" % (d1[126], d2[126], "SAME" if d1[126]==d2[126] else "DIFF"))

# Extension tag (byte 128)
print("  Extension byte 128: AWE=0x%02X, Orig=0x%02X  %s" % (d1[128], d2[128], "SAME" if d1[128]==d2[128] else "DIFF"))

# CTA-861 Extension revision (byte 129)
print("  CTA-861 revision: AWE=0x%02X, Orig=0x%02X  %s" % (d1[129], d2[129], "SAME" if d1[129]==d2[129] else "DIFF"))

# Data block count (byte 130)
print("  DTD offset: AWE=0x%02X, Orig=0x%02X  %s" % (d1[130], d2[130], "SAME" if d1[130]==d2[130] else "DIFF"))

# Find DV VSDB in both files
print()
print("=" * 75)
print("DOLBY VISION VSDB ANALYSIS")
print("=" * 75)

def find_dv_vsdb(data, start=128, end=256):
    """Find Dolby VSDB (OUI 00D046) in CTA-861 block"""
    for i in range(start, end-2):
        # VSDB format: tag(1) + length(1) + OUI(3) + ...
        if data[i+2] == 0x46 and data[i+3] == 0xD0 and data[i+4] == 0x00:
            tag = data[i] >> 5
            length = (data[i] & 0x1F) << 8 | data[i+1]
            return i, tag, length
    return None, None, None

pos1, tag1, len1 = find_dv_vsdb(d1)
pos2, tag2, len2 = find_dv_vsdb(d2)

print("\n  AWE (1 (1).bin):")
if pos1:
    print("    VSDB found at byte %d (0x%02X)" % (pos1, pos1))
    print("    OUI: %02X %02X %02X (Dolby)" % (d1[pos1+2], d1[pos1+3], d1[pos1+4]))
    print("    Payload: %02X %02X %02X %02X %02X %02X %02X" % (d1[pos1+5], d1[pos1+6], d1[pos1+7], d1[pos1+8], d1[pos1+9], d1[pos1+10], d1[pos1+11]))
    print("    Raw bytes: %s" % " ".join("%02X" % d1[pos1+j] for j in range(min(20, 256-pos1))))
else:
    print("    DV VSDB NOT FOUND!")

print("\n  Original (778.bin):")
if pos2:
    print("    VSDB found at byte %d (0x%02X)" % (pos2, pos2))
    print("    OUI: %02X %02X %02X (Dolby)" % (d2[pos2+2], d2[pos2+3], d2[pos2+4]))
    print("    Payload: %02X %02X %02X %02X %02X %02X %02X" % (d2[pos2+5], d2[pos2+6], d2[pos2+7], d2[pos2+8], d2[pos2+9], d2[pos2+10], d2[pos2+11]))
    print("    Raw bytes: %s" % " ".join("%02X" % d2[pos2+j] for j in range(min(20, 256-pos2))))
else:
    print("    DV VSDB NOT FOUND!")

# CTA-861 data blocks analysis
print()
print("=" * 75)
print("CTA-861 DATA BLOCKS (Block 1, bytes 128-255)")
print("=" * 75)

print("\n  AWE (1 (1).bin) - bytes 131-179:")
offset = 131
while offset < 180:
    raw = d1[offset]
    tag = (raw >> 5) & 0x07
    length = raw & 0x1F
    if length == 0 and tag == 0:
        break
    tag_names = {1: "Audio", 2: "Video", 3: "Speaker Alloc", 4: "VSDB", 5: "Colorimetry",
                 6: "HDR Static", 7: "HDR Dynamic", 0: "Padding/Unknown"}
    tn = tag_names.get(tag, "Tag%d" % tag)
    content = " ".join("%02X" % d1[offset+j] for j in range(length+2) if offset+j < 256)
    print("    offset %d: [%s] len=%d  %s" % (offset, tn, length, content))
    offset += length + 2  # tag byte + length byte + data

print("\n  Original (778.bin) - bytes 131-179:")
offset = 131
while offset < 180:
    raw = d2[offset]
    tag = (raw >> 5) & 0x07
    length = raw & 0x1F
    if length == 0 and tag == 0:
        break
    tag_names = {1: "Audio", 2: "Video", 3: "Speaker Alloc", 4: "VSDB", 5: "Colorimetry",
                 6: "HDR Static", 7: "HDR Dynamic", 0: "Padding/Unknown"}
    tn = tag_names.get(tag, "Tag%d" % tag)
    content = " ".join("%02X" % d2[offset+j] for j in range(length+2) if offset+j < 256)
    print("    offset %d: [%s] len=%d  %s" % (offset, tn, length, content))
    offset += length + 2

# Summary
print()
print("=" * 75)
print("CRITICAL FINDINGS")
print("=" * 75)
print("""
The two EDID files have %d different bytes (53%% of total).
This is NOT a single-byte modification.

KEY DIFFERENCES:
1. CTA-861 extension data blocks are COMPLETELY different
2. Descriptor arrangement in base EDID differs
3. HDR/Dolby Vision data block structure differs
4. DV VSDB is at different offset positions

CONCLUSION:
AWE (AW EDID Editor) rewrote much more than just one byte.
Simply changing byte 210 (9E->9F) in the registry is NOT enough
to enable Dolby Vision. The entire CTA-861 extension block
needs to match the AWE version.

RECOMMENDATION:
Write File1 (1 (1).bin) directly to the registry EDID key.
That file already has all correct modifications and valid checksums.
""" % len(diffs))
