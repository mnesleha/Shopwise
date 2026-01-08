param(
  [Parameter(Mandatory = $true)]
  [string]$EnvFile
)

if (-not (Test-Path $EnvFile)) {
  throw "Env file not found: $EnvFile"
}

Get-Content $EnvFile | ForEach-Object {
  $line = $_.Trim()
  if ($line -eq "" -or $line.StartsWith("#")) { return }
  # split only on first '='
  $parts = $line.Split("=", 2)
  if ($parts.Length -ne 2) { return }

  $key = $parts[0].Trim()
  $val = $parts[1].Trim()

  # Strip optional surrounding quotes
  if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
    $val = $val.Substring(1, $val.Length - 2)
  }

  Set-Item -Path ("Env:\{0}" -f $key) -Value $val
}

Write-Host "Environment variables loaded from $EnvFile"