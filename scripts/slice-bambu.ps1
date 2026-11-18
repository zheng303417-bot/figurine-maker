param(
    [Parameter(Mandatory)][string]$Mesh,
    [Parameter(Mandatory)][string]$Output,
    [string]$Bambu = "C:\Program Files\Bambu Studio\bambu-studio.exe",
    [switch]$EnableSupport
)
$ErrorActionPreference = "Stop"
$app = (Resolve-Path -LiteralPath $Bambu).Path
$model = (Resolve-Path -LiteralPath $Mesh).Path
$destination = New-Item -ItemType Directory -Force -Path $Output
$profiles = Join-Path (Split-Path -Parent $app) "resources/profiles/BBL"
$machine = Join-Path $profiles "machine/Bambu Lab A1 0.4 nozzle.json"
$process = Join-Path $profiles "process/0.20mm Standard @BBL A1.json"
$filament = Join-Path $profiles "filament/Bambu PLA Basic @BBL A1.json"

function Read-Profile([string]$Path, [int]$Depth = 0) {
    if ($Depth -gt 10) { throw "Invalid profile inheritance: $Path" }
    $child = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json -AsHashtable
    $expanded = [ordered]@{}
    if ($child.inherits) {
        $parent = Join-Path (Split-Path -Parent $Path) ($child.inherits + ".json")
        $expanded = Read-Profile $parent ($Depth + 1)
    }
    foreach ($key in $child.Keys) {
        if ($key -ne "inherits") { $expanded[$key] = $child[$key] }
    }
    return $expanded
}

$machineFlat = Join-Path $destination.FullName "machine.json"
$processFlat = Join-Path $destination.FullName "process.json"
$filamentFlat = Join-Path $destination.FullName "filament.json"
Read-Profile $machine | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $machineFlat -Encoding utf8NoBOM
$processSettings = Read-Profile $process
if ($EnableSupport) { $processSettings["enable_support"] = "1" }
$processSettings | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $processFlat -Encoding utf8NoBOM
Read-Profile $filament | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $filamentFlat -Encoding utf8NoBOM
$argsForSlicer = @(
    '--load-settings', ('"{0};{1}"' -f $machineFlat, $processFlat),
    '--load-filaments', ('"{0}"' -f $filamentFlat),
    '--debug', '4', '--arrange', '1', '--orient', '0', '--slice', '0',
    '--outputdir', ('"{0}"' -f $destination.FullName),
    '--export-3mf', 'sliced.3mf', ('"{0}"' -f $model)
)
$runner = Start-Process -FilePath $app -ArgumentList $argsForSlicer -WorkingDirectory $destination.FullName -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $destination.FullName "slice.log") `
    -RedirectStandardError (Join-Path $destination.FullName "slice-errors.log")
if (-not $runner.WaitForExit(180000)) {
    $runner.Kill()
    throw "Bambu Studio timed out."
}
if ($runner.ExitCode -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $destination.FullName "sliced.3mf"))) {
    throw "Bambu Studio exit $($runner.ExitCode). Check sliced.3mf, slice.log and slice-errors.log."
}
Write-Output (Join-Path $destination.FullName "sliced.3mf")
