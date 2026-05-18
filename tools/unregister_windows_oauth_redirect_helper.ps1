$ErrorActionPreference = "Stop"

$schemeKey = "HKCU:\Software\Classes\com.buderus.tt.dashtt"

if (Test-Path -LiteralPath $schemeKey) {
    Remove-Item -LiteralPath $schemeKey -Recurse -Force
    Write-Host "Removed Windows URL handler for com.buderus.tt.dashtt://"
}
else {
    Write-Host "No Windows URL handler for com.buderus.tt.dashtt:// was registered."
}
