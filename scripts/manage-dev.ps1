param(
  [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
  [string[]]$CommandArgs
)

. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.dev"

python backend/manage.py @CommandArgs
