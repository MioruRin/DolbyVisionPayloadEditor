$p = 'HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\XMI27B3\5&3b3aafbd&0&UID4352\Device Parameters'
$edid = (Get-ItemProperty -Path $p -Name EDID).EDID
$len = $edid.Length

Write-Host "EDID: $len bytes"

# Byte 210
$b210 = $edid[210]
if ($b210 -lt 0) { $b210 += 256 }
Write-Host "Byte 210: 0x$([Convert]::ToString($b210,16).ToUpper())"

# Payload bytes 208-214
$payload = @()
for ($i = 208; $i -le 214; $i++) {
    $x = $edid[$i]
    if ($x -lt 0) { $x += 256 }
    $payload += $x.ToString('X2')
}
Write-Host "Payload: $($payload -join ' ')"

# Checksum verification
for ($blk = 0; $blk -lt 3; $blk++) {
    $sum = 0
    $st = $blk * 128
    for ($j = 0; $j -lt 128; $j++) {
        $x = $edid[$st + $j]
        if ($x -lt 0) { $x += 256 }
        $sum += $x
    }
    $mod = $sum % 256
    $cs = $edid[$st + 127]
    if ($cs -lt 0) { $cs += 256 }
    if ($mod -eq 0) {
        Write-Host "Block $blk CS 0x$($cs.ToString('X2')): OK"
    } else {
        Write-Host "Block $blk CS 0x$($cs.ToString('X2')): FAIL (mod=$mod)"
    }
}

Write-Host ""
if ($b210 -eq 0x9F) {
    Write-Host "RESULT: PATCH APPLIED - Byte 210 is 0x9F"
} else {
    Write-Host "RESULT: NOT PATCHED - Byte 210 is 0x$([Convert]::ToString($b210,16).ToUpper())"
}
