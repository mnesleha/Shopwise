param(
  [switch]$NoReset
)

. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.test"

if ($NoReset) {
  python backend/manage.py seed_test_data --profile e2e
}
else {
  python backend/manage.py seed_test_data --profile e2e --reset
}
