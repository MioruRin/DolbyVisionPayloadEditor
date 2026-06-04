# patch_edid_simple.ps1
# 用途：将 XMI27B3 显示器 EDID 中 4D0A9E58 改为 4D0A9F58
# 用法：以管理员身份运行此脚本
#
# 修改内容：
#   Byte 210: 0x9E -> 0x9F
#   同时仅重算 Block 1（128-255）的校验和

$ErrorActionPreference = 'Stop'
$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\XMI27B3\5&3b3aafbd&0&UID4352\Device Parameters'

Write-Host '=== EDID Patch Script (9E->9F) ===' -ForegroundColor Cyan

# 1. 读取当前 EDID
Write-Host '[1/5] Reading current EDID from registry...'
try {
    $prop = Get-ItemProperty -Path $regPath -Name 'EDID'
    $bytes = $prop.EDID
} catch {
    Write-Host 'ERROR: Cannot read EDID.' -ForegroundColor Red
    Write-Host $_.Exception.Message
    Read-Host 'Press Enter to exit'
    exit 1
}
Write-Host "      Read $($bytes.Length) bytes"

# 2. 验证目标字节是否存在
Write-Host '[2/5] Verifying target bytes at position 208...'
$expected = @(0x4D, 0x0A, 0x9E, 0x58, 0x98, 0xAA, 0x5C)
$ok = $true
for ($i = 0; $i -lt 7; $i++) {
    if ($bytes[208 + $i] -ne $expected[$i]) { $ok = $false }
}
if (-not $ok) {
    Write-Host 'ERROR: Target bytes 4D0A9E58... NOT found at byte 208' -ForegroundColor Red
    Read-Host 'Press Enter to exit'
    exit 1
}
Write-Host '      [OK] Target found'

# 3. 备份原始 EDID → Temp 目录
Write-Host '[3/5] Backing up original EDID...'
$tempDir = [System.IO.Path]::GetTempPath()
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupPath = Join-Path $tempDir "EDID_XMI27B3_original_${ts}.bin"
[System.IO.File]::WriteAllBytes($backupPath, $bytes)
Write-Host "      Backup: $backupPath"

# 4. 执行修改 + 重算校验和
Write-Host '[4/5] Patching byte 210 (0x9E -> 0x9F) and recalculating checksum...'
$bytes[210] = 0x9F

# 仅重算 Block 1（byte 128~255）的校验和
# EDID 校验和规则：前 127 字节之和 mod 256，校验和 = (0 - sum) mod 256
$sum = 0
for ($i = 128; $i -lt 255; $i++) {
    $b = $bytes[$i]
    if ($b -lt 0) { $b = $b + 256 }
    $sum += $b
}
$correctCS = (0x100 - ($sum % 0x100)) % 0x100
$oldCS = $bytes[255]
$bytes[255] = $correctCS
Write-Host "      Block 1 checksum: 0x$([Convert]::ToString($oldCS,16).ToUpper()) -> 0x$([Convert]::ToString($correctCS,16).ToUpper())"

# 5. 验证 Block 1 校验和
Write-Host '[5/5] Validating Block 1 checksum...'
$sum2 = 0
for ($i = 128; $i -lt 256; $i++) {
    $b = $bytes[$i]
    if ($b -lt 0) { $b = $b + 256 }
    $sum2 += $b
}
if (($sum2 % 256) -eq 0) {
    Write-Host '      [OK] Block 1 checksum valid (sum mod 256 = 0)'
} else {
    Write-Host "      [ERROR] Block 1 checksum INVALID (sum mod 256 = $($sum2 % 256))" -ForegroundColor Red
    Read-Host 'Press Enter to exit'
    exit 1
}

# 6. 写入注册表
Write-Host ''
Write-Host 'Writing patched EDID to registry...'
try {
    # 取得当前用户对注册表项的写权限
    $acl = Get-Acl $regPath
    $user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $rule = New-Object System.Security.AccessControl.RegistryAccessRule($user, 'FullControl', 'Allow')
    $acl.SetAccessRule($rule)
    Set-Acl -Path $regPath -AclObject $acl

    Set-ItemProperty -Path $regPath -Name 'EDID' -Value $bytes -Type Binary -Force
    Write-Host '[SUCCESS] EDID written to registry!' -ForegroundColor Green
} catch {
    Write-Host '[ERROR] Failed to write EDID:' -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host ''
    Write-Host 'Try running this script as Administrator.' -ForegroundColor Yellow
    Read-Host 'Press Enter to exit'
    exit 1
}

Write-Host ''
Write-Host '=== NEXT STEPS ===' -ForegroundColor Cyan
Write-Host '1. Unplug and replug your monitor DP/HDMI cable, OR'
Write-Host '2. Device Manager -> Display adapters -> Right-click -> Disable, then Enable'
Write-Host ''
Write-Host "Backup (if you need to restore): $backupPath"
Write-Host ''

Read-Host 'Press Enter to exit'
