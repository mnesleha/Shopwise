. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.test"

Set-Location "$PSScriptRoot\..\backend"
pytest -m mysql --ds=config.settings.local
