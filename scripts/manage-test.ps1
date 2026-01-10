param(
  [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
  [string[]]$CommandArgs
)

. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.test"

python backend/manage.py @CommandArgs
