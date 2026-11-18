param([string]$Python = "python")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$tools = Join-Path $root ".tools/hunyuan"
$source = Join-Path $tools "source"
$weights = Join-Path $tools "weights"
$deps = Join-Path $tools "deps"
$revision = "f8db63096c8282cb27354314d896feba5ba6ff8a"
New-Item -ItemType Directory -Force -Path $weights | Out-Null

function Run-Native([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable exited with code $LASTEXITCODE." }
}

if (-not (Test-Path -LiteralPath (Join-Path $root ".tools/triposr/deps-cpu/torch/__init__.py"))) {
    & (Join-Path $PSScriptRoot "setup-triposr.ps1") -Python $Python -Device cpu
}
if (-not (Test-Path -LiteralPath (Join-Path $source ".git"))) {
    Run-Native git @("clone", "https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git", $source)
}
if ((git -C $source rev-parse HEAD) -ne $revision) {
    Run-Native git @("-C", $source, "checkout", "--detach", $revision)
}
$decoder = Join-Path $source "hy3dgen/shapegen/models/autoencoders/volume_decoders.py"
$body = Get-Content -Raw -LiteralPath $decoder
$old = "next_points = torch.stack(nidx, dim=1)`r`n            next_points = (next_points *"
$new = "next_points = torch.stack(nidx, dim=1).to(dtype)`r`n            next_points = (next_points *"
if ($body.Contains($old)) {
    $body.Replace($old, $new) | Set-Content -LiteralPath $decoder -NoNewline -Encoding utf8
} elseif ($body.Contains($old.Replace("`r`n", "`n"))) {
    $body.Replace($old.Replace("`r`n", "`n"), $new.Replace("`r`n", "`n")) |
        Set-Content -LiteralPath $decoder -NoNewline -Encoding utf8
} elseif (-not $body.Contains("next_points = torch.stack(nidx, dim=1).to(dtype)")) {
    throw "The pinned Hunyuan3D decoder has an unexpected layout."
}

if (-not (Test-Path -LiteralPath (Join-Path $deps "torchvision/__init__.py"))) {
    Run-Native $Python @("-m", "pip", "install", "--only-binary=:all:", "--no-deps", "--target", $deps,
        "--index-url", "https://download.pytorch.org/whl/cpu", "torchvision==0.22.1")
}
if (-not (Test-Path -LiteralPath (Join-Path $deps "diffusers/__init__.py"))) {
    Run-Native $Python @("-m", "pip", "install", "--only-binary=:all:", "--no-deps", "--target", $deps,
        "diffusers==0.33.1")
}

$url = "https://huggingface.co/tencent/Hunyuan3D-2mini/resolve/f90a0f7/hunyuan3d-dit-v2-mini-turbo"
$checkpoint = Join-Path $weights "model.fp16.safetensors"
if (-not (Test-Path -LiteralPath $checkpoint) -or (Get-Item -LiteralPath $checkpoint).Length -lt 3822584202) {
    Run-Native curl.exe @("-fL", "--retry", "2", "--continue-at", "-", "--output", $checkpoint,
        "$url/model.fp16.safetensors")
}
$expected = "bdbcef30dd0149a281e17d5b5b1fdad1122c904e098a42f3100e04e03c247bc4"
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $checkpoint).Hash -ne $expected) {
    throw "Hunyuan3D checkpoint SHA-256 mismatch."
}
$config = Join-Path $weights "config.yaml"
if (-not (Test-Path -LiteralPath $config)) {
    Run-Native curl.exe @("-fL", "--retry", "2", "--output", $config, "$url/config.yaml")
}
Write-Output "Hunyuan3D files ready at $tools"
