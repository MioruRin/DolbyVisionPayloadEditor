# patch_edid_final.ps1
# 功能：将 XMI27B3 显示器 EDID 中
#       4D0A9E5898AA5C 改为 4D0A9F5898AA5C
#       并重新计算受影响块的校验和，写入注册表
#
# 用法：右键此文件 -> 以管理员身份运行
#        或在管理员 PowerShell 中执行：
#        Set-ExecutionPolicy Bypass -Scope Process
#        .\patch_edid_final.ps1

$ErrorActionPreference = 'Stop'
$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\XMI27B3\5&3b3aafbd&0&UID4352\Device Parameters'

Write-Host "=== EDID Patch: 9E -> 9F ===" -ForegroundColor Cyan

# ---------- 1. 读取当前 EDID ----------
try {
    $prop = Get-ItemProperty -Path $regPath -Name 'EDID'
    $edidBytes = $prop.EDID
} catch {
    Write-Host "[ERROR] Cannot read EDID from registry." -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "Read EDID: $($edidBytes.Length) bytes"

# ---------- 2. 确认目标值 ----------
# 目标在 byte 208~214: 4D 0A 9E 58 98 AA 5C
$targetPos = 208
$origBytes = @(0x4D,0x0A,0x9E,0x58,0x98,0xAA,0x5C)
$match = $true
for ($i = 0; $i -lt 7; $i++) {
    if ($edidBytes[$targetPos + $i] -ne $origBytes[$i]) { $match = $false }
}
if (-not $match) {
    Write-Host "[ERROR] Target bytes 4D0A9E58... not found at byte $targetPos" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Target found at byte $targetPos (4D0A9E5898AA5C)"

# ---------- 3. 备份原始 EDID ----------
$tempDir = [System.IO.Path]::GetTempPath()
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupFile = Join-Path $tempDir "EDID_XMI27B3_original_${ts}.bin"
# 写二进制备份
[System.IO.File]::WriteAllBytes($backupFile, $edidBytes)
Write-Host "[OK] Backup saved: $backupFile"

# ---------- 4. 执行修改 ----------
$edidBytes[210] = 0x9F   # byte 210: 0x9E -> 0x9F
$newPayload = ($edidBytes[208..214] | ForEach-Object { $_.ToString('X2') }) -join ' '
Write-Host "[OK] Patched: 4D 0A 9E 58 -> 4D 0A 9F 58"
Write-Host "      New payload: $newPayload"

# ---------- 5. 重新计算校验和 ----------
# EDID 每 128 字节一块，最后一字节为校验和
# 规则：块内所有 128 字节之和 mod 256 == 0
function Set-BlockChecksum($data, $blockIndex) {
    $start = $blockIndex * 128
    # 先算不含校验和字节的总和
    $sum = 0
    for ($i = 0; $i -lt 127; $i++) {
        $b = $data[$start + $i]
        if ($b -lt 0) { $b = $b + 256 }
        $sum += $b
    }
    $oldCS = $data[$start + 127]
    # 正确校验和 = (0 - sum) mod 256
    $correctCS = (0x100 - ($sum % 0x100)) % 0x100
    $data[$start + 127] = $correctCS
    $oldHex = '{0:X2}' -f [byte]$oldCS
    $newHex = '{0:X2}' -f [byte]$correctCS
    Write-Host "  Block $blockIndex (byte $start-$($start+127)): 0x$oldHex -> 0x$newHex"
}

$totalBlocks = [Math]::Floor($edidBytes.Length / 128)
Write-Host "`nRecalculating checksums for $totalBlocks block(s)..."
for ($blk = 0; $blk -lt $totalBlocks; $blk++) {
    Set-BlockChecksum $edidBytes $blk
}

# ---------- 6. 验证 ----------
Write-Host "`nValidation:"
$allOK = $true
for ($blk = 0; $blk -lt $totalBlocks; $blk++) {
    $start = $blk * 128
    $sum = 0
    for ($i = 0; $i -lt 128; $i++) {
        $b = $edidBytes[$start + $i]
        if ($b -lt 0) { $b = $b + 256 }
        $sum += $b
    }
    $mod = $sum % 256
    $status = if ($mod -eq 0) { 'OK' } else { "FAIL (sum%256=$mod)" }
    if ($mod -ne 0) { $allOK = $false }
    Write-Host "  Block $blk : $status"
}
if (-not $allOK) {
    Write-Host "[ERROR] Checksum validation FAILED!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# ---------- 7. 写入注册表 ----------
try {
    # 尝试取得写权限（修改 ACL）
    $acl = Get-Acl $regPath
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $rule = New-Object System.Security.AccessControl.RegistryAccessRule(
        $currentUser, 'FullControl', 'Allow'
    )
    $acl.SetAccessRule($rule)
    Set-Acl -Path $regPath -AclObject $acl
    Write-Host "`n[OK] Registry ACL updated for $currentUser"
} catch {
    Write-Host "`n[WARNING] Could not modify ACL (may already have permission): $($_.Exception.Message)" -ForegroundColor Yellow
}

try {
    Set-ItemProperty -Path $regPath -Name 'EDID' -Value $edidBytes -Type Binary -Force
    Write-Host "`n[SUCCESS] EDID written to registry!" -ForegroundColor Green
    Write-Host "Path: $regPath"
} catch {
    Write-Host "`n[ERROR] Failed to write EDID to registry:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "`nTry running this script as Administrator." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# ---------- 8. 提示后续操作 ----------
Write-Host "`n>>> NEXT STEPS <<<" -ForegroundColor Cyan
Write-Host "1. Unplug and replug your monitor's DP/HDMI cable, OR"
Write-Host "2. Device Manager -> Display adapters -> Disable, then Enable"
Write-Host "`nBackup file: $backupFile"
Write-Host "(If anything goes wrong, you can restore using this backup)`n"

Read-Host "Press Enter to exit"
