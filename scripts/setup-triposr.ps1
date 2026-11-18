param(
    [string]$Python = "python",
    [ValidateSet("cuda", "cpu")][string]$Device = "cpu"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$tools = Join-Path $root ".tools/triposr"
$source = Join-Path $tools "source"
$weights = Join-Path $tools "weights"
$extra = Join-Path $tools "extra"
$temporary = Join-Path $tools "tmp"
$revision = "107cefdc244c39106fa830359024f6a2f1c78871"
$dependencies = Join-Path $tools "deps"
if ($Device -eq "cpu") { $dependencies = Join-Path $tools "deps-cpu" }
New-Item -ItemType Directory -Force -Path $weights,$temporary | Out-Null

function Invoke-Step {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable exited with code $LASTEXITCODE." }
}

function Download-File {
    param([string]$Url, [string]$Path)
    $arguments = @("--fail", "--location", "--retry", "2", "--output", $Path)
    if (Test-Path -LiteralPath $Path) { $arguments += @("--continue-at", "-") }
    Invoke-Step curl.exe ($arguments + $Url)
}

if (-not (Test-Path -LiteralPath (Join-Path $source ".git"))) {
    Invoke-Step git @("clone", "https://github.com/VAST-AI-Research/TripoSR.git", $source)
}
Invoke-Step git @("-C", $source, "checkout", "--detach", $revision)
$env:TEMP = $temporary
$env:TMP = $temporary
$env:PIP_CACHE_DIR = Join-Path $temporary "pip-cache"
$pipArgs = @("-m", "pip", "install", "--disable-pip-version-check", "--target", $dependencies)
if ($Device -eq "cuda") {
    $pipArgs += @("--index-url", "https://download.pytorch.org/whl/cu126")
}
if (-not (Test-Path -LiteralPath (Join-Path $dependencies "torch/__init__.py"))) {
    Invoke-Step $Python ($pipArgs + @("torch==2.7.1"))
}
if (-not (Test-Path -LiteralPath (Join-Path $extra "rembg/__init__.py"))) {
    Invoke-Step $Python @("-m", "pip", "install", "--disable-pip-version-check", "--target",
        $extra, "-r", (Join-Path $root "runtime/triposr-requirements.txt"))
}

$hf = "https://huggingface.co/stabilityai/TripoSR/resolve/5b52193"
$checkpoint = Join-Path $weights "model.ckpt"
$sha = "429e2c6b22a0923967459de24d67f05962b235f79cde6b032aa7ed2ffcd970ee"
if (-not (Test-Path -LiteralPath $checkpoint) -or (Get-Item -LiteralPath $checkpoint).Length -lt 1677246742) {
    Download-File "$hf/model.ckpt" $checkpoint
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $checkpoint).Hash -ne $sha) {
    throw "TripoSR checkpoint SHA-256 does not match the published checkpoint."
}
if (-not (Test-Path -LiteralPath (Join-Path $weights "config.yaml"))) {
    Download-File "$hf/config.yaml" (Join-Path $weights "config.yaml")
}
if (-not (Test-Path -LiteralPath (Join-Path $weights "dino-config.json"))) {
    Download-File "https://huggingface.co/facebook/dino-vitb16/resolve/main/config.json" (Join-Path $weights "dino-config.json")
}
$background = Join-Path $weights "u2netp.onnx"
if (-not (Test-Path -LiteralPath $background) -or (Get-Item -LiteralPath $background).Length -lt 4574861) {
    Download-File "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx" $background
}
if ((Get-FileHash -Algorithm MD5 -LiteralPath $background).Hash -ne "8e83ca70e441ab06c318d82300c84806") {
    throw "U2NetP content does not match the rembg checksum."
}
Write-Output "TripoSR files ready at $tools"
