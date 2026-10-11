# First run: starts both auto-restarting containers. Open Docker Desktop first.
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python -m scripts.check_docker_config
    if ($LASTEXITCODE -ne 0) { throw 'Complete .env.local before starting Aether AI.' }

    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is not running yet.' }

    docker compose up --build --detach
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose could not start Aether AI.' }

    docker compose ps
    Write-Host 'Aether AI dashboard: http://127.0.0.1:8080'
    Write-Host 'New paper entries remain paused until you sign in and allow them.'
} finally {
    Pop-Location
}
