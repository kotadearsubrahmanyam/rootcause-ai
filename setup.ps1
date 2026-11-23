$ErrorActionPreference = 'Stop'
$path = Join-Path $PSScriptRoot '.env'
if (Test-Path -LiteralPath $path) { Write-Output 'Local configuration already exists.'; return }
function New-LocalSecret {
    $bytes = [byte[]]::new(32)
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($bytes)
}
$values = (Get-Content -Raw (Join-Path $PSScriptRoot '.env.example')).Replace('NEXTAUTH_SECRET=', "NEXTAUTH_SECRET=$(New-LocalSecret)").Replace('POSTGRES_PASSWORD=', "POSTGRES_PASSWORD=$(New-LocalSecret)")
[IO.File]::WriteAllText($path, $values)
Write-Output 'Created local configuration.'
