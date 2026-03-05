. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.dev"
python backend/manage.py runserver 0.0.0.0:8000
