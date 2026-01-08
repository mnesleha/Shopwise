. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.test"
python backend/manage.py runserver 8001
