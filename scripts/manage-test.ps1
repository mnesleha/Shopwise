param(
  [Parameter(Mandatory = $true)]
  [string[]]$Args
)

. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.test"

python backend/manage.py @Args
