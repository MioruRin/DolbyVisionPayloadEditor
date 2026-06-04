import sys

f1 = r'C:\Users\MioruRin\Downloads\1 (1).bin'
f2 = r'C:\Users\MioruRin\Desktop\778.bin'

with open(f1, 'rb') as fh:
    d1 = fh.read()
with open(f2, 'rb') as fh:
    d2 = fh.read()

print("File 1 (Downloads): %d bytes" % len(d1))
print("File 2 (Desktop 778): %d bytes" % len(d2))
print()

diffs = []
maxlen = max(len(d1), len(d2))
for i in range(maxlen):
    b1 = d1[i] if i < len(d1) else None
    b2 = d2[i] if i < len(d2) else None
    if b1 != b2:
        diffs.append((i, b1, b2))

print("Total differences: %d" % len(diffs))
print()
print("%-8s %-12s %-16s %-16s %s" % ("#", "Offset", "File1(Down)", "File2(778)", "Note"))
print("-" * 75)

for idx, (offset, b1, b2) in enumerate(diffs):
    h1 = "0x%02X" % b1 if b1 is not None else "N/A"
    h2 = "0x%02X" % b2 if b2 is not None else "N/A"
    note = ""
    if offset in (127, 255, 383):
        note = "<-- CHECKSUM"
    elif offset == 210:
        note = "<-- TARGET BYTE"
    elif 205 <= offset <= 214:
        note = "<-- DV VSDB"
    elif b1 == 0x94 and b2 == 0x93:
        note = "<-- Block1 CS"
    print("%-8d %-12s %-16s %-16s %s" % (idx+1, "%d (0x%02X)" % (offset, offset), h1, h2, note))

# Show hex dump context around each difference
print()
print("=" * 75)
print("HEX CONTEXT AROUND DIFFERENCES")
print("=" * 75)

for offset, b1, b2 in diffs:
    ctx_start = max(0, offset - 4)
    ctx_end = min(maxlen, offset + 5)
    part1 = []
    part2 = []
    for i in range(ctx_start, ctx_end):
        if i < len(d1):
            part1.append("%02X" % d1[i])
        else:
            part1.append("??")
        if i < len(d2):
            part2.append("%02X" % d2[i])
        else:
            part2.append("??")
    print()
    print("At offset %d (0x%02X):" % (offset, offset))
    print("  File1: ...%s..." % " ".join(part1))
    print("  File2: ...%s..." % " ".join(part2))
