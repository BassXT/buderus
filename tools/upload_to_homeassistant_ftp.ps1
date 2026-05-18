param(
    [Parameter(Mandatory = $true)]
    [string]$HostName,
    [Parameter(Mandatory = $true)]
    [string]$Username,
    [string]$PasswordFile = ".analysis\ha_ftp_password.txt",
    [string]$LocalIntegrationPath = "custom_components\buderus_ha",
    [switch]$DeletePasswordFile
)

$ErrorActionPreference = "Stop"

function New-FtpUri {
    param(
        [string]$HostName,
        [string]$Path
    )

    $cleanPath = $Path.TrimStart("/")
    return [Uri]("ftp://$HostName/$cleanPath")
}

function New-FtpRequest {
    param(
        [string]$HostName,
        [string]$Path,
        [string]$Method,
        [System.Net.NetworkCredential]$Credential
    )

    $request = [System.Net.FtpWebRequest]::Create((New-FtpUri -HostName $HostName -Path $Path))
    $request.Method = $Method
    $request.Credentials = $Credential
    $request.UseBinary = $true
    $request.UsePassive = $true
    $request.KeepAlive = $false
    return $request
}

function Invoke-FtpList {
    param(
        [string]$HostName,
        [string]$Path,
        [System.Net.NetworkCredential]$Credential
    )

    $request = New-FtpRequest -HostName $HostName -Path $Path -Method ([System.Net.WebRequestMethods+Ftp]::ListDirectory) -Credential $Credential
    $response = $request.GetResponse()
    try {
        $reader = [System.IO.StreamReader]::new($response.GetResponseStream())
        try {
            return @($reader.ReadToEnd() -split "`r?`n" | Where-Object { $_ })
        }
        finally {
            $reader.Dispose()
        }
    }
    finally {
        $response.Dispose()
    }
}

function Ensure-FtpDirectory {
    param(
        [string]$HostName,
        [string]$Path,
        [System.Net.NetworkCredential]$Credential
    )

    $parts = @($Path.Trim("/") -split "/" | Where-Object { $_ })
    $current = ""
    foreach ($part in $parts) {
        $current = if ($current) { "$current/$part" } else { $part }
        $request = New-FtpRequest -HostName $HostName -Path $current -Method ([System.Net.WebRequestMethods+Ftp]::MakeDirectory) -Credential $Credential
        try {
            $response = $request.GetResponse()
            $response.Dispose()
        }
        catch [System.Net.WebException] {
            $ftpResponse = [System.Net.FtpWebResponse]$_.Exception.Response
            if ($ftpResponse) {
                $status = [int]$ftpResponse.StatusCode
                $ftpResponse.Dispose()
                if ($status -eq 550) {
                    continue
                }
            }
            throw
        }
    }
}

function Upload-FtpFile {
    param(
        [string]$HostName,
        [string]$RemotePath,
        [string]$LocalPath,
        [System.Net.NetworkCredential]$Credential
    )

    $request = New-FtpRequest -HostName $HostName -Path $RemotePath -Method ([System.Net.WebRequestMethods+Ftp]::UploadFile) -Credential $Credential
    $source = [System.IO.File]::OpenRead($LocalPath)
    try {
        $target = $request.GetRequestStream()
        try {
            $source.CopyTo($target)
        }
        finally {
            $target.Dispose()
        }
    }
    finally {
        $source.Dispose()
    }

    $response = $request.GetResponse()
    $response.Dispose()
}

function Get-RemoteBasePath {
    param(
        [string]$HostName,
        [System.Net.NetworkCredential]$Credential
    )

    $rootItems = Invoke-FtpList -HostName $HostName -Path "/" -Credential $Credential
    if ($rootItems -contains "configuration.yaml" -or $rootItems -contains "custom_components") {
        return "custom_components/buderus_ha"
    }
    if ($rootItems -contains "config") {
        return "config/custom_components/buderus_ha"
    }

    Write-Host "Could not infer FTP root. Root entries:"
    $rootItems | ForEach-Object { Write-Host " - $_" }
    throw "Set the correct remote base path in this script after checking the FTP root."
}

$resolvedLocalPath = (Resolve-Path -LiteralPath $LocalIntegrationPath).Path
if (-not (Test-Path -LiteralPath $PasswordFile)) {
    throw "Password file not found: $PasswordFile"
}

$password = (Get-Content -LiteralPath $PasswordFile -Raw).Trim()
if (-not $password) {
    throw "Password file is empty: $PasswordFile"
}

$credential = [System.Net.NetworkCredential]::new($Username, $password)
$remoteBasePath = Get-RemoteBasePath -HostName $HostName -Credential $credential

$localBasePath = $resolvedLocalPath.TrimEnd("\", "/")

Write-Host "Uploading $resolvedLocalPath to ftp://$HostName/$remoteBasePath"
Ensure-FtpDirectory -HostName $HostName -Path $remoteBasePath -Credential $credential

$files = Get-ChildItem -LiteralPath $resolvedLocalPath -Recurse -File | Where-Object {
    $_.FullName -notmatch "\\__pycache__\\" -and $_.Name -notlike "*.pyc"
}

foreach ($file in $files) {
    $relative = $file.FullName.Substring($localBasePath.Length).TrimStart("\", "/").Replace("\", "/")
    $remotePath = "$remoteBasePath/$relative"
    $remoteDirectory = Split-Path -Path $remotePath -Parent
    Ensure-FtpDirectory -HostName $HostName -Path $remoteDirectory.Replace("\", "/") -Credential $credential
    Upload-FtpFile -HostName $HostName -RemotePath $remotePath -LocalPath $file.FullName -Credential $credential
    Write-Host "Uploaded $relative"
}

if ($DeletePasswordFile) {
    Remove-Item -LiteralPath $PasswordFile -Force
}

Write-Host "Upload complete. Restart Home Assistant before adding or reloading the integration."
