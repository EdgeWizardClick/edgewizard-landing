param(
  [string]$RepoRoot = "C:\Users\koeni\OneDrive\Desktop\EdgeWizard\edgewizard-landing",
  [string]$JsonPath = "flags.json",
  [string]$TemplatePath = "flags/_template/index.html",
  [string]$CommitMessage = "Build flag landing pages"
)

$ErrorActionPreference = "Stop"

Set-Location $RepoRoot

if (-not (Test-Path $JsonPath)) {
  throw "flags.json nicht gefunden im Repo-Root. Erwartet: $RepoRoot\$JsonPath"
}
if (-not (Test-Path $TemplatePath)) {
  throw "Template nicht gefunden. Erwartet: $RepoRoot\$TemplatePath (zuerst Schritt 1 ausfuehren)"
}

$template = Get-Content $TemplatePath -Raw -Encoding UTF8
$flags = Get-Content $JsonPath -Raw -Encoding UTF8 | ConvertFrom-Json

function Ensure-Dir($p) {
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

function Set-HeadMeta([string]$html, [string]$title, [string]$desc) {
  # <title>
  if ($html -match '(?is)<title>.*?</title>') {
    $html = [regex]::Replace($html, '(?is)<title>.*?</title>', "<title>$title</title>")
  } else {
    $html = [regex]::Replace($html, '(?is)</head>', "  <title>$title</title>`n</head>")
  }

  # meta description (insert if missing, replace if present)
  if ($html -match '(?is)<meta\s+name=["'']description["'']\s+content=["''][^"'']*["'']\s*/?>') {
    $html = [regex]::Replace(
      $html,
      '(?is)<meta\s+name=["'']description["'']\s+content=["''][^"'']*["'']\s*/?>',
      "<meta name=`"description`" content=`"$desc`" />"
    )
  } else {
    $html = [regex]::Replace($html, '(?is)</head>', "  <meta name=`"description`" content=`"$desc`" />`n</head>")
  }

  return $html
}

function Inject-FlagBlock([string]$html, [string]$slug, [string]$h2, [string]$lead) {
  $before = "/flags/$slug/assets/${slug}_before.png"
  $after  = "/flags/$slug/assets/${slug}_after.png"

  $block = @"
<h2 class="page-title">$h2</h2>

<div class="compare">
  <figure class="shot">
    <img src="$before" alt="$h2 before" loading="lazy" decoding="async">
    <figcaption>Before</figcaption>
  </figure>
  <figure class="shot">
    <img src="$after" alt="$h2 after" loading="lazy" decoding="async">
    <figcaption>After</figcaption>
  </figure>
</div>

<p class="page-lead">$lead</p>

<p class="page-link">
  <a href="/" class="backlink">edgewizard.click</a>
</p>

"@

  $needle = "High-end edge detection with clean"
  if ($html -notmatch [regex]::Escape($needle)) {
    throw "Template passt nicht: Einfuegepunkt '$needle' nicht gefunden."
  }

  # Falls bereits ein Block existiert: entfernen (idempotent)
  $html = [regex]::Replace(
    $html,
    '(?is)<h2 class="page-title">.*?<a href="/" class="backlink">edgewizard\.click</a>\s*</p>\s*',
    ''
  )

  $html = $html -replace [regex]::Escape($needle), ($block + $needle)

  # CSS nur einmal hinzufuegen
  if ($html -notmatch "\.compare\s*\{") {
    $css = @"
  .page-title{margin:1.2rem 0 .6rem 0;font-size:clamp(1.05rem,1.5vw,1.2rem);font-weight:600;color:var(--color-text-primary);}
  .page-lead{margin:.2rem 0 1.1rem 0;color:var(--color-text-secondary);font-size:clamp(.98rem,1.45vw,1.08rem);line-height:1.6;}
  .page-link{margin:0 0 1.2rem 0;}
  .backlink{color:var(--color-text-secondary);text-decoration:none;border-bottom:1px solid rgba(229,229,229,.25);}
  .backlink:hover{color:var(--color-text-primary);border-bottom-color:rgba(255,255,255,.6);}
  .compare{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin:1rem auto 1rem;max-width:720px;}
  .shot{margin:0;padding:.75rem;border-radius:14px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);}
  .shot img{width:100%;height:auto;display:block;border-radius:10px;}
  .shot figcaption{margin:.55rem 0 0 0;font-size:.9rem;letter-spacing:.04em;color:var(--color-text-secondary);text-transform:uppercase;}
  @media (max-width:640px){.compare{grid-template-columns:1fr;}}
"@
    $html = $html -replace "(?is)</style>", ($css + "`n</style>")
  }

  return $html
}

foreach ($f in $flags) {
  $slug = $f.slug
  $h2   = $f.h2
  $lead = $f.lead

  if (-not $slug -or -not $h2 -or -not $lead) {
    throw "flags.json Eintrag unvollstaendig. Erwartet: slug, h2, lead."
  }

  $outDir = "flags/$slug"
  $assets = "$outDir/assets"
  Ensure-Dir $outDir
  Ensure-Dir $assets

  $b = "$assets/${slug}_before.png"
  $a = "$assets/${slug}_after.png"
  if (-not (Test-Path $b)) { Write-Warning "Fehlt: $RepoRoot\$b" }
  if (-not (Test-Path $a)) { Write-Warning "Fehlt: $RepoRoot\$a" }

  $metaTitle = if ($f.metaTitle) { $f.metaTitle } else { "$h2 | EdgeWizard" }
  $metaDesc  = if ($f.metaDescription) { $f.metaDescription } else { $lead }

  $html = $template
  $html = Set-HeadMeta $html $metaTitle $metaDesc
  $html = Inject-FlagBlock $html $slug $h2 $lead

  Set-Content -Path "$outDir/index.html" -Value $html -Encoding UTF8
}

git add -A
$changes = git status --porcelain
if ($changes) {
  git commit -m $CommitMessage
  git push
  "OK: Build + Push abgeschlossen."
} else {
  "Keine Aenderungen zu committen."
}
