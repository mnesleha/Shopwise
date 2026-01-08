param(
  [Parameter(Mandatory = $true)]
  [string[]]$Args
)

. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.dev"

python backend/manage.py @Args
