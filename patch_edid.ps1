# patch_edid.ps1 - 修改 EDID 中 4D0A9E58 -> 4D0A9F58，重算校验和，写入注册表

# 以无符号方式计算单块校验和
function Get-CorrectChecksum($blockBytes) {
    $sum = 0
    for ($i = 0; $i -lt 128; $i++) {
        $b = $blockBytes[$i]
        if ($b -lt 0) { $b = $b + 256 }
        $sum += $b
    }
    $checksum = (0x100 - ($sum % 0x100)) % 0x100
    return $checksum
}

# 完整 EDID（384 字节 = 3 个 128 字节块）
$edidHex = '00FFFFFFFFFFFF0061A9B3270000000002240103803C22782A0F91AE5243B0260F505421080081C081408180B3009500A9C00101010108E80030F2705A80B0588A0055502100001E6FC200A0A0A055503020350055502100001A000000FC004D69204D6F6E69746F720A2020000000FD0018A00FFFA0000A202020202020010C02037EF1E278024B6110601F5D12037576403F320F7F073D07C05F7E0715075057060167040783010000E200FFE305C3016B030C002000B8442F0020036DD85DC40178806B0230A0C36521EB0146D0004D0A9E5898AA5CE5018B8490016F1A0000030B30A00060A0019305A00065FBBB1A0101E30F8501E6060D018B7302009402032EF1FA2A0001FF0E6F089F01FF0E6F088F01FF099F059F01FF099F058FEE2A00017F0737049F017F0737048F565E00A0A0A029503020350055502100001A000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000BC'

# 转为无符号字节数组
$bytes = @()
for ($i = 0; $i -lt $edidHex.Length; $i += 2) {
    $b = [Convert]::ToByte($edidHex.Substring($i, 2), 16)
    $bytes += $b
}

Write-Host "=== EDID Patch Script ==="
Write-Host "Original EDID $($bytes.Length) bytes"

# 确认目标值存在
$tgt = @(0x4D, 0x0A, 0x9E, 0x58, 0x98, 0xAA, 0x5C)
$match = $true
for ($k = 0; $k -lt 7; $k++) {
    if ($bytes[208 + $k] -ne $tgt[$k]) { $match = $false }
}
if (-not $match) {
    Write-Host "[ERROR] Payload 4D0A9E58... not found at byte 208. Aborting." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Payload found at byte 208"

# 修改：Byte 210 从 0x9E 改为 0x9F
$bytes[210] = 0x9F
Write-Host "Patched: byte 210 0x9E -> 0x9F"

# 重新计算每个 128 字节块的校验和
$totalBlocks = [Math]::Floor($bytes.Length / 128)
Write-Host "`nRecalculating checksums for $totalBlocks EDID blocks..."
for ($blk = 0; $blk -lt $totalBlocks; $blk++) {
    $start = $blk * 128
    $block = $bytes[$start..($start + 127)]
    $oldCS = $block[127]
    # 计算总和（无符号）
    $sum = 0
    for ($j = 0; $j -lt 128; $j++) {
        $b = $block[$j]
        if ($b -lt 0) { $b = $b + 256 }
        $sum += $b
    }
    $correctCS = (0x100 - (($sum - $oldCS) % 0x100)) % 0x100
    $bytes[$start + 127] = $correctCS
    $oldHex = [Convert]::ToString([byte]$oldCS, 16).ToUpper().PadLeft(2, '0')
    $newHex = [Convert]::ToString([byte]$correctCS, 16).ToUpper().PadLeft(2, '0')
    Write-Host "  Block $blk (byte ${start}-$($start+127)): 0x$oldHex -> 0x$newHex"
}

# 验证
Write-Host "`nValidation (each block sum mod 256 should be 0):"
$allOK = $true
for ($blk = 0; $blk -lt $totalBlocks; $blk++) {
    $start = $blk * 128
    $sum = 0
    for ($j = 0; $j -lt 128; $j++) {
        $b = $bytes[$start + $j]
        if ($b -lt 0) { $b = $b + 256 }
        $sum += $b
    }
    $mod = $sum % 256
    $status = if ($mod -eq 0) { 'OK' } else { "FAIL (mod=$mod)" }
    if ($mod -ne 0) { $allOK = $false }
    Write-Host "  Block $blk : $status"
}
if (-not $allOK) {
    Write-Host "[ERROR] Checksum validation failed!" -ForegroundColor Red
    exit 1
}

# 输出完整新 HEX
$newHex = ($bytes | ForEach-Object { $_.ToString('X2') }) -join ''
Write-Host "`n=== NEW EDID HEX (768 chars) ==="
Write-Host $newHex
Write-Host "=== END HEX ==="

# 保存备份和新 EDID 到 Temp 目录
$tempDir = [System.IO.Path]::GetTempPath()
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupFile = Join-Path $tempDir "EDID_XMI27B3_backup_${ts}.txt"
$newFile     = Join-Path $tempDir "EDID_XMI27B3_new_${ts}.txt"

# 原始 EDID 备份（用原始 hex 字符串）
Set-Content -Path $backupFile -Value $edidHex -Encoding ASCII -NoNewline

# 新 EDID 保存
$newHex = ($bytes | ForEach-Object { $_.ToString('X2') }) -join ''
Set-Content -Path $newFile -Value $newHex -Encoding ASCII -NoNewline
Write-Host "`nBackup (original): $backupFile"
Write-Host "New EDID saved to: $newFile"

# 写入注册表
$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\XMI27B3\5&3b3aafbd&0&UID4352\Device Parameters'

try {
    # 尝试取得所有权并修改权限
    $regKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey(
        'SYSTEM\CurrentControlSet\Enum\DISPLAY\XMI27B3\5&3b3aafbd&0&UID4352\Device Parameters',
        [Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree,
        [System.Security.AccessControl.RegistryRights]::TakeOwnership
    )
    if ($regKey) { $regKey.Close() }

    # 写入
    Set-ItemProperty -Path $regPath -Name 'EDID' -Value $bytes -Type Binary -Force
    Write-Host "`n[SUCCESS] EDID written to registry!" -ForegroundColor Green
    Write-Host "Path: $regPath"
    Write-Host "`n>>> Action required: Replug DP/HDMI cable or disable/enable display adapter."
} catch {
    Write-Host "`n[WARNING] Cannot write to registry: $_" -ForegroundColor Yellow
    Write-Host "`n===== MANUAL STEPS ====="
    Write-Host "1. Run regedit.exe as Administrator"
    Write-Host "2. Navigate to:"
    Write-Host "   HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\DISPLAY"
    Write-Host "   \XMI27B3\5&3b3aafbd&0&UID4352\Device Parameters"
    Write-Host "3. Double-click 'EDID' (REG_BINARY)"
    Write-Host "4. Replace ALL hex values with the NEW EDID HEX printed above"
    Write-Host "5. Click OK, then replug the monitor cable"
    Write-Host "======================="
    Write-Host "`nNew EDID also saved to: $newFile"
}
