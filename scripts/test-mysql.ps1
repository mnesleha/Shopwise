. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.test"

pytest -m mysql --ds=config.settings.local
