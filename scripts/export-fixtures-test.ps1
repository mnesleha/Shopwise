param(
  [string]$OutPath = "artifacts\fixtures.json"
)

. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.test"

New-Item -ItemType Directory -Force -Path (Split-Path $OutPath) | Out-Null
python backend/manage.py seed_test_data --profile e2e --export-fixtures $OutPath
Write-Host "Exported: $OutPath"
