$ErrorActionPreference = "Stop"

$captureScript = Join-Path $PSScriptRoot "capture_windows_oauth_redirect.ps1"
$schemeKey = "HKCU:\Software\Classes\com.buderus.tt.dashtt"
$commandKey = Join-Path $schemeKey "shell\open\command"
$command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$captureScript`" `"%1`""

New-Item -Path $schemeKey -Force | Out-Null
New-ItemProperty -Path $schemeKey -Name "(default)" -Value "URL:Buderus MX300 OAuth Redirect" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $schemeKey -Name "URL Protocol" -Value "" -PropertyType String -Force | Out-Null
New-Item -Path $commandKey -Force | Out-Null
Set-ItemProperty -Path $commandKey -Name "(default)" -Value $command

Write-Host "Registered Windows URL handler for com.buderus.tt.dashtt://"
Write-Host "When the browser asks to open the external app after SingleKey login, allow it."
Write-Host "The final redirect URL will be copied to the clipboard."
