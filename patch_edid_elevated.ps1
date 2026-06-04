# patch_edid_elevated.ps1 - 自动申请 UAC 管理员权限修改 EDID
# 双击运行，弹出 UAC 后点"是"即可

# 自动以管理员身份重新运行本脚本
if (!([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "请求管理员权限..." -ForegroundColor Yellow
    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Process powershell.exe "-ExecutionPolicy Bypass -File `"$scriptPath`"" -Verb RunAs
    exit
}

# ========== 以下代码以管理员权限运行 ==========

$regPath = "HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\XMI27B3\5&3b3aafbd&0&UID4352\Device Parameters"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  EDID 修改工具（管理员模式）" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 读取当前 EDID
Write-Host "[1/6] 读取注册表 EDID..." -ForegroundColor Yellow
try {
    $edid = (Get-ItemProperty -Path $regPath -Name EDID -ErrorAction Stop).EDID
    Write-Host "       成功读取 $($edid.Length) 字节" -ForegroundColor Green
} catch {
    Write-Host "       读取失败: $_" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

# 2. 显示修改前关键字节
Write-Host "[2/6] 检查目标字节..." -ForegroundColor Yellow
$before = '{0:X2}' -f [byte]$edid[210]
Write-Host "       Byte 210 (修改前): 0x$before"

# 3. 备份原始 EDID 到 Temp 目录
Write-Host "[3/6] 备份原始 EDID..." -ForegroundColor Yellow
$tempDir = [System.IO.Path]::GetTempPath()
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $tempDir "EDID_XMI27B3_original_${ts}.bin"
[System.IO.File]::WriteAllBytes($backupPath, $edid)
Write-Host "       备份到: $backupPath" -ForegroundColor Green

# 4. 执行修改：byte 210: 0x9E → 0x9F
Write-Host "[4/6] 修改 Byte 210: 0x$before → 0x9F..." -ForegroundColor Yellow
$edid[210] = 0x9F

# 5. 重算 Block 1（字节 128-255）校验和
# EDID 规则：每块 128 字节，块内所有字节之和 mod 256 == 0
Write-Host "[5/6] 重算 Block 1 校验和..." -ForegroundColor Yellow
$sum = 0
for ($i = 128; $i -lt 255; $i++) {
    $b = $edid[$i]
    if ($b -lt 0) { $b = $b + 256 }
    $sum += $b
}
$correctCS = (0x100 - ($sum % 0x100)) % 0x100
$oldCS = $edid[255]
$edid[255] = $correctCS
Write-Host "       Block 1 校验和: 0x$([Convert]::ToString($oldCS,16).ToUpper()) → 0x$([Convert]::ToString($correctCS,16).ToUpper())" -ForegroundColor Green

# 验证所有块校验和
$allOK = $true
for ($blk = 0; $blk -lt 3; $blk++) {
    $st = $blk * 128
    $s = 0
    for ($j = 0; $j -lt 128; $j++) {
        $b = $edid[$st + $j]
        if ($b -lt 0) { $b = $b + 256 }
        $s += $b
    }
    if ($s % 256 -eq 0) {
        Write-Host "       Block $blk 校验和: OK (0x$([Convert]::ToString([byte]$edid[$st+127],16).ToUpper()))" -ForegroundColor Green
    } else {
        Write-Host "       Block $blk 校验和: FAIL" -ForegroundColor Red
        $allOK = $false
    }
}

# 6. 写回注册表
Write-Host "[6/6] 写入注册表..." -ForegroundColor Yellow
try {
    Set-ItemProperty -Path $regPath -Name EDID -Value $edid -Type Binary
    Write-Host "       写入成功！" -ForegroundColor Green
} catch {
    Write-Host "       写入失败: $_" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

# 验证写入结果
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
$verify = (Get-ItemProperty -Path $regPath -Name EDID).EDID
$after = '{0:X2}' -f [byte]$verify[210]
if ($verify[210] -eq 0x9F) {
    Write-Host "✅ 验证通过！Byte 210 = 0x$after" -ForegroundColor Green
    Write-Host ""
    Write-Host "请重新插拔 DP/HDMI 线，或设备管理器禁用/启用显示器使修改生效。" -ForegroundColor Cyan
} else {
    Write-Host "❌ 验证失败！Byte 210 = 0x$after，期望值 0x9F" -ForegroundColor Red
}

Write-Host ""
Read-Host "按回车退出"
