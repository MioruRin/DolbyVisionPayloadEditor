# restore_clean_edid.ps1
# Writes the CLEAN patched EDID (778.bin + 9E->9F only) to registry
# Run in ADMIN PowerShell

$path = 'HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\XMI27B3\5&3b3aafbd&0&UID4352\Device Parameters'
$binPath = 'C:\Users\MioruRin\Desktop\XMI27B3_DV_clean.bin'

Write-Host 'Reading clean patched EDID...'
$bytes = [System.IO.File]::ReadAllBytes($binPath)
Write-Host ("EDID: " + $bytes.Length + " bytes")
Write-Host ("Byte 210: 0x" + $bytes[210].ToString('X2'))

Write-Host 'Writing to registry...'
Set-ItemProperty -Path $path -Name EDID -Value $bytes -Type Binary

Write-Host 'Verifying...'
$v = (Get-ItemProperty -Path $path -Name EDID).EDID
Write-Host ("Registry EDID: " + $v.Length + " bytes")
Write-Host ("Byte 210: 0x" + $v[210].ToString('X2'))
if ($v[210] -eq 0x9F) {
    Write-Host 'SUCCESS: Clean EDID written!' -ForegroundColor Green
} else {
    Write-Host 'FAIL: Byte 210 is not 0x9F' -ForegroundColor Red
}

Write-Host 'Press Enter to exit...'
Read-Host
