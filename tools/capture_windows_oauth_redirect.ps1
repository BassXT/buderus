param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$RedirectUrl
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $repoRoot ".analysis\auth"
$outFile = Join-Path $outDir "last_redirect_url.txt"

New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Set-Content -LiteralPath $outFile -Value $RedirectUrl -Encoding UTF8

try {
    Set-Clipboard -Value $RedirectUrl
    Write-Host "Buderus MX300 OAuth redirect copied to clipboard."
}
catch {
    Write-Host "Could not copy redirect to clipboard. It was saved here:"
    Write-Host $outFile
}

Write-Host ""
Write-Host "Return to Home Assistant and paste the redirect URL into the setup form."
Write-Host ""
Write-Host $RedirectUrl
Start-Sleep -Seconds 8
