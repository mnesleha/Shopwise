param(
  [switch]$Reset
)

. "$PSScriptRoot\env.ps1" -EnvFile "backend\.env.dev"

if ($Reset) {
  python backend/manage.py seed_test_data --profile e2e --reset
}
else {
  python backend/manage.py seed_test_data --profile e2e
}
