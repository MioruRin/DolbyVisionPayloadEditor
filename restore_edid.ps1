# restore_edid.ps1 - Restore original EDID and apply patch
# Run this in ADMIN PowerShell

$path = "HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\XMI27B3\5&3b3aafbd&0&UID4352\Device Parameters"

# 修改后的 EDID（byte 210 = 0x9F，Block 1 checksum 已重算为 0x93）
$edidHex = '00FFFFFFFFFFFF0061A9B3270000000002240103803C22782A0F91AE5243B0260F505421080081C081408180B3009500A9C00101010108E80030F2705A80B0588A0055502100001E6FC200A0A0A055503020350055502100001A000000FC004D69204D6F6E69746F720A2020000000FD0018A00FFFA0000A202020202020010C02037EF1E278024B6110601F5D12037576403F320F7F073D07C05F7E0715075057060167040783010000E200FFE305C3016B030C002000B8442F0020036DD85DC40178806B0230A0C36521EB0146D0004D0A9F5898AA5CE5018B8490016F1A0000030B30A00060A0019305A00065FBBB1A0101E30F8501E6060D018B7302009302032EF1FA2A0001FF0E6F089F01FF0E6F088F01FF099F059F01FF099F058FEE2A00017F0737049F017F0737048F565E00A0A0A029503020350055502100001A000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000BC'

# hex -> bytes
$bytes = @()
for ($i = 0; $i -lt $edidHex.Length; $i += 2) {
    $bytes += [Convert]::ToByte($edidHex.Substring($i, 2), 16)
}

Write-Host "Restoring EDID... ($($bytes.Length) bytes)"

# 验证校验和
for ($blk = 0; $blk -lt 3; $blk++) {
    $st = $blk * 128
    $sum = 0
    for ($j = 0; $j -lt 128; $j++) {
        $b = $bytes[$st + $j]
        if ($b -lt 0) { $b = $b + 256 }
        $sum += $b
    }
    $mod = $sum % 256
    if ($mod -eq 0) {
        Write-Host "  Block $blk checksum: OK" -ForegroundColor Green
    } else {
        Write-Host "  Block $blk checksum: FAIL ($mod)" -ForegroundColor Red
    }
}

# 写回注册表
Set-ItemProperty -Path $path -Name EDID -Value $bytes -Type Binary

# 验证
$verify = (Get-ItemProperty -Path $path -Name EDID).EDID
Write-Host ""
if ($verify.Length -eq 384) {
    Write-Host "[OK] EDID restored: $($verify.Length) bytes" -ForegroundColor Green
    $b210 = if ($verify[210] -lt 0) { $verify[210] + 256 } else { $verify[210] }
    Write-Host "[OK] Byte 210 = 0x$([Convert]::ToString($b210, 16).ToUpper())" -ForegroundColor Green
} else {
    Write-Host "[FAIL] EDID length = $($verify.Length), expected 384" -ForegroundColor Red
}
