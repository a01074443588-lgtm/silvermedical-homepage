[CmdletBinding()]
param(
    [string]$Url = "https://staff.silvermedical.kr/staff/"
)

$ErrorActionPreference = "Stop"
$utf8 = [Text.Encoding]::UTF8
$decodeText = {
    param([string]$Value)
    $utf8.GetString([Convert]::FromBase64String($Value))
}

$desktop = [Environment]::GetFolderPath("Desktop")
$installDirectory = Join-Path $env:LOCALAPPDATA "SilverMedicalLauncher"
$shortcutName = & $decodeText "7Iuk67KE66mU65SU7LusIOq0gOumrOyEvO2EsC5sbms="
$shortcutPath = Join-Path $desktop $shortcutName
$iconSource = Join-Path $PSScriptRoot "favicon.ico"
$iconPath = Join-Path $installDirectory "favicon.ico"

New-Item -ItemType Directory -Force -Path $installDirectory | Out-Null
Copy-Item -LiteralPath $iconSource -Destination $iconPath -Force

$chromeCandidates = @(
    (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
)
$chromePath = $chromeCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = & $decodeText "7Iuk67KE66mU65SU7LusIO2ZiO2OmOydtOyngOyZgCDsmrTsmIEg6rSA66asIO2ZlOuptOydhCDsl73ri4jri6Qu"

if ($chromePath) {
    $shortcut.TargetPath = $chromePath
    $shortcut.Arguments = "--app=$Url"
    $shortcut.WorkingDirectory = Split-Path -Parent $chromePath
} else {
    $shortcut.TargetPath = Join-Path $env:WINDIR "explorer.exe"
    $shortcut.Arguments = $Url
}

$shortcut.Save()
$message = & $decodeText "6rSA66as7J6QIOufsOyymOulvCDrp4zrk6Tsl4jsirXri4jri6Q6IA=="
Write-Host "$message$shortcutPath" -ForegroundColor Green
