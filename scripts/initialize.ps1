param(
    [string]$Python = "python",
    [string]$Blender
)
$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
if ($Blender) {
    $env:FIGURINE_BLENDER = (Resolve-Path -LiteralPath $Blender).Path
}
$env:PYTHONPATH = Join-Path $project "runtime"
& $Python -m figurine_runtime probe
if ($LASTEXITCODE -ne 0) {
    throw "Runtime probe failed."
}
