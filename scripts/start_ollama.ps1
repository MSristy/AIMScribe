$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path -Parent $PSScriptRoot
$demoOllama = Join-Path $demoRoot '.local\ollama\ollama.exe'
if (-not (Test-Path -LiteralPath $demoOllama)) {
    throw 'Portable runtime missing. Run python scripts/setup_local_ollama.py first.'
}
try {
    $demoVersion = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 3
    Write-Output "Ollama already running: $($demoVersion.version)"
    exit 0
} catch {
    # Start only when no existing local server responds.
}
$env:OLLAMA_MODELS = Join-Path $demoRoot '.local\models'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
Start-Process -FilePath $demoOllama -ArgumentList 'serve' -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $demoRoot '.local\ollama\server.stdout.log') `
    -RedirectStandardError (Join-Path $demoRoot '.local\ollama\server.stderr.log') | Out-Null
Write-Output 'Ollama started on http://127.0.0.1:11434 (local model store, cloud disabled).'
