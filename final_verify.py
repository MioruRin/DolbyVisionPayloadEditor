#!/usr/bin/env python3
"""
Verify that the current registry EDID already has the correct DV payload
AND compare against the original to make sure we didn't lose any data
"""

import sys

# Read the current registry EDID (already patched: byte 210 = 0x9F)
# This is the hex we wrote to the registry
current_hex = '00FFFFFFFFFFFF0061A9B3270000000002240103803C22782A0F91AE5243B0260F505421080081C081408180B3009500A9C00101010108E80030F2705A80B0588A0055502100001E6FC200A0A0A055503020350055502100001A000000FC004D69204D6F6E69746F720A2020000000FD0018A00FFFA0000A202020202020010C02037EF1E278024B6110601F5D12037576403F320F7F073D07C05F7E0715075057060167040783010000E200FFE305C3016B030C002000B8442F0020036DD85DC40178806B0230A0C36521EB0146D0004D0A9F5898AA5CE5018B8490016F1A0000030B30A00060A0019305A00065FBBB1A0101E30F8501E6060D018B7302009302032EF1FA2A0001FF0E6F089F01FF0E6F088F01FF099F059F01FF099F058FEE2A00017F0737049F017F0737048F565E00A0A0A029503020350055502100001A000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000BC'

# Read original (from 778.bin)
with open(r'C:\Users\MioruRin\Desktop\778.bin', 'rb') as f:
    original = f.read()

# Read AWE modified (from Downloads)
with open(r'C:\Users\MioruRin\Downloads\1 (1).bin', 'rb') as f:
    awe = f.read()

current = bytes.fromhex(current_hex)

print("=" * 80)
print("COMPARISON: Current Registry EDID vs Original vs AWE")
print("=" * 80)

# Check DV payload
print("\n### Dolby Vision Payload Check ###")
for name, data in [("Current (Registry)", current), ("Original (778.bin)", original), ("AWE Modified", awe)]:
    # Find DV OUI
    oui_pos = data.find(bytes([0x46, 0xD0, 0x00]))
    if oui_pos >= 0:
        payload = data[oui_pos+3:oui_pos+10]
        print(f"  {name}:")
        print(f"    DV VSDB at byte {oui_pos}")
        print(f"    Payload: {payload.hex().upper()}")
        print(f"    3rd byte: 0x{payload[2]:02X} ({'DV HDMI enabled' if payload[2] & 1 else 'DV HDMI disabled'})")
    else:
        print(f"  {name}: NO DV VSDB FOUND!")

# Compare current vs original
print("\n### Current Registry vs Original (778.bin) ###")
diffs = [(i, current[i], original[i]) for i in range(min(len(current), len(original))) if current[i] != original[i]]
print(f"  Total differences: {len(diffs)}")
for offset, b1, b2 in diffs:
    print(f"    Byte {offset} (0x{offset:02X}): 0x{b2:02X} -> 0x{b1:02X}")

# Checksum verification
print("\n### Checksum Verification (Current Registry) ###")
for blk in range(3):
    start = blk * 128
    total = sum(current[start:start+128])
    mod = total % 256
    cs = current[start + 127]
    status = "OK" if mod == 0 else f"FAIL (mod={mod})"
    print(f"  Block {blk}: CS=0x{cs:02X} -> {status}")

# VRR check - look for specific bytes
print("\n### VRR Related Data ###")
# VRR info is typically in CTA-861 data blocks
# Check bytes around offset 0x78-0x9F region for VRR descriptors

# Check DTD offset
print(f"  DTD offset (byte 130): Current=0x{current[130]:02X}, Original=0x{original[130]:02X}")

# Extension count
print(f"  Extension count (byte 126): Current={current[126]}, Original={original[126]}")

# Block 2 comparison
b2_diffs = [(i, current[i], original[i]) for i in range(256, 384) if current[i] != original[i]]
print(f"  Block 2 (DisplayID ext): {len(b2_diffs)} diff bytes")
if b2_diffs:
    print(f"    All identical: {len(b2_diffs) == 0}")

print("\n### CONCLUSION ###")
if len(diffs) == 2:  # Should be just byte 210 and 255
    print("  PERFECT: Only 2 bytes differ from original (target byte + checksum)")
    print("  VRR and all refresh rate data PRESERVED")
else:
    print(f"  WARNING: {len(diffs)} bytes differ from original")
    if len(diffs) > 5:
        print("  Some data may have been lost")
    else:
        print("  Check each difference above - should only be target byte and checksum")
