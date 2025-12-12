param(
  [string]$Root = (Resolve-Path ".").Path,
  [string]$Template = ".\templates\flag-template.html",
  [string]$FlagsJson = ".\flags.json"
)

Set-Location $Root

if (-not (Test-Path $Template)) { throw "Template fehlt: $Template" }
if (-not (Test-Path $FlagsJson)) { throw "flags.json fehlt: $FlagsJson" }

$templateHtml = Get-Content $Template -Raw
$flags = Get-Content $FlagsJson -Raw | ConvertFrom-Json

foreach ($f in $flags) {
  $slug  = $f.slug
  $title = $f.title
  $h2    = $f.h2
  $lead  = $f.lead

  if ([string]::IsNullOrWhiteSpace($slug)) { throw "slug fehlt in flags.json Eintrag." }

  $dir = Join-Path $Root ("flags\" + $slug)
  $assetsDir = Join-Path $dir "assets"
  New-Item -ItemType Directory -Force -Path $assetsDir | Out-Null

  # Erwartete Bilder
  $before = Join-Path $assetsDir ("{0}_before.png" -f $slug)
  $after  = Join-Path $assetsDir ("{0}_after.png" -f $slug)

  if (-not (Test-Path $before)) {
    Write-Host "WARN: fehlt $before" -ForegroundColor Yellow
  }
  if (-not (Test-Path $after)) {
    Write-Host "WARN: fehlt $after" -ForegroundColor Yellow
  }

  $out = $templateHtml
  $out = $out -replace "\{\{SLUG\}\}",  [regex]::Escape($slug)  -replace "\\", ""
  $out = $out -replace "\{\{TITLE\}\}", [System.Text.RegularExpressions.Regex]::Escape($title) -replace "\\", ""
  $out = $out -replace "\{\{H2\}\}",    [System.Text.RegularExpressions.Regex]::Escape($h2)    -replace "\\", ""
  $out = $out -replace "\{\{LEAD\}\}",  [System.Text.RegularExpressions.Regex]::Escape($lead)  -replace "\\", ""

  $indexPath = Join-Path $dir "index.html"
  Set-Content $indexPath $out -Encoding UTF8

  Write-Host ("OK: flags/{0}/index.html" -f $slug) -ForegroundColor Green
}

Write-Host "Fertig. Prüfe warnings (fehlende Bilder) und pushe dann." -ForegroundColor Cyan
