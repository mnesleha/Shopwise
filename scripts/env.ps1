param(
  [Parameter(Mandatory = $true)]
  [string]$EnvFile
)

if (-not (Test-Path $EnvFile)) {
  throw "Env file not found: $EnvFile"
}

# Clear known app-specific environment variables first
$varsToClear = @(
  "DJANGO_SETTINGS_MODULE",
  "SECRET_KEY",
  "GUEST_ACCESS_TOKEN_PEPPER",
  "SENTRY_ENABLED",
  "SENTRY_ENVIRONMENT",
  "DEFAULT_FROM_EMAIL",

  "DB_NAME",
  "DB_USER",
  "DB_PASSWORD",
  "DB_HOST",
  "DB_PORT",

  "R2_ACCESS_KEY_ID",
  "R2_SECRET_ACCESS_KEY",
  "R2_BUCKET_NAME",
  "R2_ENDPOINT_URL",
  "R2_REGION",
  "R2_PUBLIC_DOMAIN",

  "EMAIL_BACKEND",
  "EMAIL_HOST",
  "EMAIL_PORT",
  "EMAIL_TIMEOUT",
  "EMAIL_USE_TLS",
  "EMAIL_USE_SSL",

  "ACQUIREMOCK_BASE_URL",
  "ACQUIREMOCK_API_KEY",
  "ACQUIREMOCK_WEBHOOK_SECRET",

  "FRONTEND_BASE_URL",
  "FRONTEND_RETURN_URL",
  "PUBLIC_BASE_URL",
  "BACKEND_ORIGIN",
  "API_BASE_URL",
  "NEXT_PUBLIC_BACKEND_ORIGIN",

  "Q_CLUSTER_WORKERS",
  "Q_CLUSTER_QUEUE_LIMIT",
  "Q_CLUSTER_TIMEOUT",
  "Q_CLUSTER_RETRY",

  "SERVE_MEDIA",
  "ENABLE_DEBUG_TOOLBAR"
)

foreach ($name in $varsToClear) {
  Remove-Item -Path ("Env:\{0}" -f $name) -ErrorAction SilentlyContinue
}

Get-Content $EnvFile | ForEach-Object {
  $line = $_.Trim()

  if ($line -eq "" -or $line.StartsWith("#")) {
    return
  }

  # split only on first '='
  $parts = $line.Split("=", 2)
  if ($parts.Length -ne 2) {
    return
  }

  $key = $parts[0].Trim()
  $val = $parts[1].Trim()

  # Strip optional surrounding quotes
  if (
    ($val.StartsWith('"') -and $val.EndsWith('"')) -or
    ($val.StartsWith("'") -and $val.EndsWith("'"))
  ) {
    $val = $val.Substring(1, $val.Length - 2)
  }

  Set-Item -Path ("Env:\{0}" -f $key) -Value $val
}

Write-Host "Environment variables loaded from $EnvFile"
Write-Host "DJANGO_SETTINGS_MODULE=$env:DJANGO_SETTINGS_MODULE"
Write-Host "DB_HOST=$env:DB_HOST"
Write-Host "DB_NAME=$env:DB_NAME"
Write-Host "R2_BUCKET_NAME=$env:R2_BUCKET_NAME"
Write-Host "R2_PUBLIC_DOMAIN=$env:R2_PUBLIC_DOMAIN"