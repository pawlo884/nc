# Konwersja src/requirements.txt na UTF-8 bez BOM (naprawa pip install)
$root = Split-Path $PSScriptRoot -Parent
$path = Join-Path $root 'src\requirements.txt'
$path = [System.IO.Path]::GetFullPath($path)
$bytes = [System.IO.File]::ReadAllBytes($path)
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
# Jesli plik ma BOM UTF-16 (FF FE) lub null bytes - traktuj jako UTF-16 LE
if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
    $text = [System.Text.Encoding]::Unicode.GetString($bytes)
} elseif ($bytes.Length -ge 2 -and $bytes[1] -eq 0x00) {
    $text = [System.Text.Encoding]::Unicode.GetString($bytes)
} else {
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
}
[System.IO.File]::WriteAllText($path, $text, $utf8NoBom)
Write-Host "Zapisano requirements.txt jako UTF-8 (bez BOM): $path"
