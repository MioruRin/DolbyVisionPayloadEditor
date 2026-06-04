#!/usr/bin/env python3
"""Export current patched EDID to a .bin file that CRU can import.
Also export the original and a diff summary for reference."""

import os

# Current registry EDID (already patched: byte 210 = 0x9F, checksums correct)
current_hex = '00FFFFFFFFFFFF0061A9B3270000000002240103803C22782A0F91AE5243B0260F505421080081C081408180B3009500A9C00101010108E80030F2705A80B0588A0055502100001E6FC200A0A0A055503020350055502100001A000000FC004D69204D6F6E69746F720A2020000000FD0018A00FFFA0000A202020202020010C02037EF1E278024B6110601F5D12037576403F320F7F073D07C05F7E0715075057060167040783010000E200FFE305C3016B030C002000B8442F0020036DD85DC40178806B0230A0C36521EB0146D0004D0A9F5898AA5CE5018B8490016F1A0000030B30A00060A0019305A00065FBBB1A0101E30F8501E6060D018B7302009302032EF1FA2A0001FF0E6F089F01FF0E6F088F01FF099F059F01FF099F058FEE2A00017F0737049F017F0737048F565E00A0A0A029503020350055502100001A000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000BC'

# Also read the original 778.bin for comparison
with open(r'C:\Users\MioruRin\Desktop\778.bin', 'rb') as f:
    original = f.read()

# Export paths
out_dir = r'C:\Users\MioruRin\Desktop'
current_bin = os.path.join(out_dir, 'XMI27B3_DV_patched.bin')
original_bin = os.path.join(out_dir, 'XMI27B3_original.bin')

current_bytes = bytes.fromhex(current_hex)

# Write current patched EDID
with open(current_bin, 'wb') as f:
    f.write(current_bytes)
print(f"Exported patched EDID: {current_bin} ({len(current_bytes)} bytes)")

# Write original
with open(original_bin, 'wb') as f:
    f.write(original)
print(f"Exported original EDID: {original_bin} ({len(original)} bytes)")

# Verify DV payload
oui_pos = current_bytes.find(bytes([0x46, 0xD0, 0x00]))
payload = current_bytes[oui_pos+3:oui_pos+10]
print(f"\nDV Payload: {payload.hex().upper()}")
print(f"3rd byte: 0x{payload[2]:02X} (bit0={'1 = DV HDMI enabled' if payload[2] & 1 else '0 = DV HDMI disabled'})")

# Checksum
for blk in range(3):
    start = blk * 128
    total = sum(current_bytes[start:start+128])
    mod = total % 256
    status = "OK" if mod == 0 else f"FAIL"
    print(f"Block {blk} checksum: {status}")

# Diff with original
diffs = [(i, current_bytes[i], original[i]) for i in range(min(len(current_bytes), len(original))) if current_bytes[i] != original[i]]
print(f"\nDifferences from original: {len(diffs)} bytes")
for offset, b1, b2 in diffs:
    label = ""
    if offset == 210: label = " <-- DV payload target byte"
    elif offset == 255: label = " <-- Block 1 checksum"
    elif offset == 127: label = " <-- Block 0 checksum"
    elif offset == 383: label = " <-- Block 2 checksum"
    print(f"  Byte {offset}: 0x{b2:02X} -> 0x{b1:02X}{label}")

print(f"\nFiles saved to Desktop:")
print(f"  - XMI27B3_DV_patched.bin  (for CRU import)")
print(f"  - XMI27B3_original.bin    (backup)")
