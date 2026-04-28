. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.test"

Set-Location "$PSScriptRoot\..\backend"
$python = Join-Path $PSScriptRoot "..\venv\Scripts\python.exe"
if (Test-Path $python) {
	& $python -m pytest -m mysql --ds=config.settings.ci_mysql
}
else {
	python -m pytest -m mysql --ds=config.settings.ci_mysql
}
