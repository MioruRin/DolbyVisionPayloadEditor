import struct

# 原始 EDID hex（384 字节）
edid_hex = '00FFFFFFFFFFFF0061A9B3270000000002240103803C22782A0F91AE5243B0260F505421080081C081408180B3009500A9C00101010108E80030F2705A80B0588A0055502100001E6FC200A0A0A055503020350055502100001A000000FC004D69204D6F6E69746F720A2020000000FD0018A00FFFA0000A202020202020010C02037EF1E278024B6110601F5D12037576403F320F7F073D07C05F7E0715075057060167040783010000E200FFE305C3016B030C002000B8442F0020036DD85DC40178806B0230A0C36521EB0146D0004D0A9E5898AA5CE5018B8490016F1A0000030B30A00060A0019305A00065FBBB1A0101E30F8501E6060D018B7302009402032EF1FA2A0001FF0E6F089F01FF0E6F088F01FF099F059F01FF099F058FEE2A00017F0737049F017F0737048F565E00A0A0A029503020350055502100001A000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000BC'

ba = bytearray(bytes.fromhex(edid_hex))
# 修改 byte 210: 0x9E -> 0x9F
ba[210] = 0x9F

# 重算 Block 1 校验和
block1_sum = sum(ba[128:255])
new_cs = (0x100 - (block1_sum % 0x100)) % 0x100
ba[255] = new_cs

print(f"Byte 210: 0x{edid_hex[420:424]} -> 0x{ba[210]:02X}")
print(f"Block 1 CS: 0x94 -> 0x{ba[255]:02X}")

# 构造 hex 数据行（每行 25 字节，用逗号分隔，末尾用反斜杠续行）
BYTES_PER_LINE = 25
hex_pairs = [f'{b:02X}' for b in ba]

lines = []
for i in range(0, len(hex_pairs), BYTES_PER_LINE):
    chunk = hex_pairs[i:i+BYTES_PER_LINE]
    line = ','.join(chunk)
    lines.append(line)

# 用反斜杠+换行拼接
continuation = []
for idx, line in enumerate(lines):
    if idx < len(lines) - 1:
        continuation.append(line + '\\')
    else:
        continuation.append(line)
joined = '\r\n'.join(continuation)

# 完整 reg 内容
reg_content = (
    'Windows Registry Editor Version 5.00\r\n'
    '\r\n'
    '[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Enum\\DISPLAY\\XMI27B3\\5&3b3aafbd&0&UID4352\\Device Parameters]\r\n'
    '"EDID"=hex:' + joined + '\r\n'
)

output_path = r'C:\Users\MioruRin\WorkBuddy\2026-06-04-13-49-05\patch_edid_v2.reg'
with open(output_path, 'wb') as f:
    # UTF-16 LE BOM
    f.write(b'\xff\xfe')
    f.write(reg_content.encode('utf-16-le'))

print(f"Saved: {output_path}")
