param(
    [string]$Token,
    [string]$GatewayId,
    [string]$OutDir = ".analysis\pointt",
    [switch]$UseClipboard
)

$ErrorActionPreference = "Stop"

if (-not $Token -and $UseClipboard) {
    $Token = Get-Clipboard
}

if (-not $Token) {
    $Token = Read-Host "Paste Bearer token or full Authorization header"
}

$Token = $Token.Trim()
$Token = $Token -replace '^authorization:\s*Bearer\s+', ''
$Token = $Token -replace '^Bearer\s+', ''

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$headers = @{
    "Authorization" = "Bearer $Token"
    "Accept" = "application/json"
    "Content-Type" = "application/json"
    "Accept-Charset" = "UTF-8"
    "User-Agent" = "DashApp/3.7.0 (iOS-Release)"
}

$base = "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1"

function Save-Json {
    param(
        [string]$Name,
        [object]$Value
    )

    $path = Join-Path $OutDir $Name
    $Value | ConvertTo-Json -Depth 80 | Set-Content -Encoding UTF8 -Path $path
    Write-Host "saved $path"
}

function Invoke-Pointt {
    param([string]$Path)

    $url = "$base$Path"
    Write-Host "GET $url"
    try {
        return Invoke-RestMethod -Method Get -Uri $url -Headers $headers
    }
    catch {
        $status = $null
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        Write-Warning "failed $Path status=$status message=$($_.Exception.Message)"
        return $null
    }
}

$gatewayList = Invoke-Pointt "/gateways/"
if (-not $gatewayList) {
    $gatewayList = Invoke-Pointt "/gateways"
}
if ($gatewayList) {
    Save-Json "gateways.json" $gatewayList
}

if (-not $GatewayId -and $gatewayList) {
    if ($gatewayList -is [array] -and $gatewayList.Count -gt 0) {
        $candidate = $gatewayList[0]
    }
    else {
        $candidate = $gatewayList
    }

    foreach ($name in @("id", "gatewayId", "deviceId", "serialId")) {
        if ($candidate.PSObject.Properties.Name -contains $name) {
            $GatewayId = [string]$candidate.$name
            break
        }
    }
}

if (-not $GatewayId) {
    Write-Host "No gateway id detected. If gateways.json contains one, rerun with -GatewayId <id>."
    exit 0
}

Write-Host "Using gateway id: $GatewayId"

$resources = @(
    "/gateways/$GatewayId",
    "/gateways/$GatewayId/partnumber",
    "/gateways/$GatewayId/resource/system/info",
    "/gateways/$GatewayId/resource/system/healthStatus",
    "/gateways/$GatewayId/resource/gateway/serialId",
    "/gateways/$GatewayId/resource/gateway/versionFirmware",
    "/gateways/$GatewayId/resource/gateway/versionHardware",
    "/gateways/$GatewayId/resource/heatingCircuits",
    "/gateways/$GatewayId/resource/dhwCircuits",
    "/gateways/$GatewayId/resource/heatSources/info",
    "/gateways/$GatewayId/resource/heatSources/chStatus",
    "/gateways/$GatewayId/resource/heatSources/actualSupplyTemperature",
    "/gateways/$GatewayId/resource/heatSources/returnTemperature",
    "/gateways/$GatewayId/resource/system/sensors/temperatures/outdoor_t1",
    "/gateways/$GatewayId/resource/heatSources/numberOfStarts",
    "/gateways/$GatewayId/resource/heatSources/workingTime/totalSystem",
    "/gateways/$GatewayId/resource/notifications"
)

foreach ($resource in $resources) {
    $result = Invoke-Pointt $resource
    if ($result) {
        $file = ($resource -replace '^/gateways/[^/]+/', '' -replace '[/?{}=]', '_' -replace '/', '__')
        Save-Json "$file.json" $result
    }
}
