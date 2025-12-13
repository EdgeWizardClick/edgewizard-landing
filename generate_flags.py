import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


# =========================
# CONFIG
# =========================
REPO = Path(r"C:\Users\koeni\OneDrive\Desktop\EdgeWizard\edgewizard-landing")
FLAGS_DIR = REPO / "flags"
MASTER = FLAGS_DIR / "afghanistan" / "index.html"
FLAGS_JSON = REPO / "flags.json"  # {"afghanistan":"Afghanistan","andorra":"Andorra",...}


# =========================
# HELPERS
# =========================
def run(cmd: List[str], cwd: Path = REPO) -> subprocess.CompletedProcess:
    """Run a command and raise with useful output on failure."""
    p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  code: {p.returncode}\n"
            f"  stdout:\n{p.stdout}\n"
            f"  stderr:\n{p.stderr}\n"
        )
    return p


def load_flags_map() -> Dict[str, str]:
    """Load slug->Country mapping. This is your safety source of truth."""
    if not FLAGS_JSON.exists():
        raise FileNotFoundError(f"flags.json fehlt: {FLAGS_JSON}")

    data = json.loads(FLAGS_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError('flags.json muss ein nicht-leeres JSON-Objekt sein: {"slug":"Country", ...}')

    out: Dict[str, str] = {}
    for slug, country in data.items():
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError("flags.json: Jeder Key (slug) muss ein nicht-leerer String sein.")
        if not isinstance(country, str) or not country.strip():
            raise ValueError(f"flags.json: Value fuer '{slug}' muss ein nicht-leerer String sein.")
        out[slug.strip()] = country.strip()

    return out


def expected_asset_paths(slug: str, country_dir: Path) -> Tuple[Path, Path]:
    assets_dir = country_dir / "assets"
    before = assets_dir / f"{slug}_before.png"
    after = assets_dir / f"{slug}_after.png"
    return before, after


def ensure_assets(slug: str, country_dir: Path) -> List[Path]:
    """Return list of missing required assets."""
    before, after = expected_asset_paths(slug, country_dir)
    missing = []
    if not before.exists():
        missing.append(before)
    if not after.exists():
        missing.append(after)
    return missing


def patch_master_to_country(master_html: str, slug: str, country: str) -> str:
    html = master_html

    # 1) <title>
    html = re.sub(
        r"<title>.*?</title>",
        f"<title>Flag of {country} – Outline & Coloring Page | EdgeWizard</title>",
        html,
        flags=re.DOTALL
    )

    # 2) meta description (fixierter Sprachstandard)
    html = re.sub(
        r'<meta\s+name="description"\s+content="[^"]*"\s*/>',
        (
            f'<meta name="description" content="This clean outline of the flag of {country} is generated with '
            f'high-precision edge detection – ideal for coloring pages, clipart and detailed line art, created with EdgeWizard." />'
        ),
        html,
        flags=re.DOTALL
    )

    # 3) <h2 class="page-title">
    html = re.sub(
        r'<h2\s+class="page-title">.*?</h2>',
        f'<h2 class="page-title">Flag of {country} – Outline & Coloring Page</h2>',
        html,
        flags=re.DOTALL
    )

    # 4) Lead Text (sichtbar)
    html = re.sub(
        r'(?s)<p\s+class="page-lead">.*?</p>',
        (
            f'<p class="page-lead">\n'
            f'  This clean outline of the {country} flag is generated with high-precision edge detection –\n'
            f'  ideal for coloring pages, clipart and detailed line art.\n'
            f'</p>'
        ),
        html
    )

    # 5) Image src: before/after immer relativ und slug-basiert
    html = re.sub(r'src="\./assets/[^"]+_before\.png"', f'src="./assets/{slug}_before.png"', html)
    html = re.sub(r'src="\./assets/[^"]+_after\.png"',  f'src="./assets/{slug}_after.png"',  html)

    # 6) ALT-Texte: finaler Standard (maximal natuerlich)
    # Before: "Flag of {Country}"
    # After:  "Flag of {Country} – Outline"
    # (wir ersetzen bewusst nur diese zwei Images – anhand der src-Pfade)
    html = re.sub(
        rf'(<img[^>]+src="\./assets/{re.escape(slug)}_before\.png"[^>]+alt=")[^"]*(")',
        rf'\1Flag of {country}\2',
        html
    )
    html = re.sub(
        rf'(<img[^>]+src="\./assets/{re.escape(slug)}_after\.png"[^>]+alt=")[^"]*(")',
        rf'\1Flag of {country} – Outline\2',
        html
    )

    # 7) Icons: immer Root assets (Single Source of Truth)
    html = re.sub(
        r'src="/assets/icon/[^"]*edgewizard_icon\.png"',
        'src="/assets/icon/edgewizard_icon.png"',
        html
    )
    html = re.sub(
        r'src="/assets/icon/[^"]*edgewizard_icon_button\.png"',
        'src="/assets/icon/edgewizard_icon_button.png"',
        html
    )

    return html


def preflight(html: str, slug: str) -> None:
    # harte Counts (Duplikate verhindern)
    def count(pat: str) -> int:
        return len(re.findall(pat, html))

    checks = {
        "page-title": count(r'<h2 class="page-title">'),
        "compare": count(r'<div class="compare">'),
        "page-lead": count(r'<p class="page-lead">'),
        "tagline": count(r'<p class="tagline">'),
        "primary-button": count(r'class="primary-button"'),
    }
    if any(v != 1 for v in checks.values()):
        raise ValueError(f"Preflight failed (Counts != 1): {checks}")

    # Pfade muessen vorhanden sein
    required = [
        '/assets/icon/edgewizard_icon.png',
        '/assets/icon/edgewizard_icon_button.png',
        f'./assets/{slug}_before.png',
        f'./assets/{slug}_after.png',
    ]
    for r in required:
        if r not in html:
            raise ValueError(f"Preflight failed (missing '{r}')")

    # Verboten: alte Pfade duerfen nicht vorkommen
    if "/Assets/Icon/" in html:
        raise ValueError("Preflight failed: forbidden '/Assets/Icon/' found in HTML")


# =========================
# MAIN
# =========================
def main() -> None:
    if not FLAGS_DIR.exists():
        raise FileNotFoundError(f"flags/ Ordner fehlt: {FLAGS_DIR}")
    if not MASTER.exists():
        raise FileNotFoundError(f"Master fehlt: {MASTER}")

    flags_map = load_flags_map()
    master_html = MASTER.read_text(encoding="utf-8")

    created: List[Path] = []
    skipped_not_in_json: List[str] = []
    skipped_missing_assets: List[Tuple[str, List[Path]]] = []

    # Wir iterieren ueber Ordner im flags/ Verzeichnis (dein "komfortabler" Workflow)
    for entry in sorted(FLAGS_DIR.iterdir()):
        if not entry.is_dir():
            continue

        slug = entry.name

        # Optional: interne Ordner ueberspringen
        if slug.startswith("_"):
            continue

        # Afghanistan ist Master (nicht automatisch neu generieren)
        if slug == "afghanistan":
            continue

        # Safety: nur generieren, wenn slug in flags.json steht
        if slug not in flags_map:
            skipped_not_in_json.append(slug)
            continue

        index_path = entry / "index.html"
        if index_path.exists():
            continue  # bereits vorhanden -> niemals automatisch ueberschreiben

        # Assets muessen vorhanden sein
        missing = ensure_assets(slug, entry)
        if missing:
            skipped_missing_assets.append((slug, missing))
            continue

        country = flags_map[slug]
        html = patch_master_to_country(master_html, slug, country)
        preflight(html, slug)

        index_path.write_text(html, encoding="utf-8")
        created.append(index_path)

    # Reporting
    if skipped_not_in_json:
        print("⏭️  Skip (nicht in flags.json eingetragen):")
        for s in skipped_not_in_json:
            print(f" - {s}")

    if skipped_missing_assets:
        print("⏭️  Skip (Assets fehlen):")
        for slug, missing in skipped_missing_assets:
            print(f" - {slug}")
            for p in missing:
                print(f"    * {p}")

    if not created:
        print("✅ Keine neuen Flag-Ordner generiert. (Entweder index.html existiert bereits oder Skips siehe oben.)")
        return

    print("✅ Neu erzeugt:")
    for p in created:
        print(" -", p)

    # Git: add/commit/push
    run(["git", "checkout", "main"])
    run(["git", "pull", "origin", "main"])

    run(["git", "add", "-A"])
    msg = f"Generate {len(created)} flag landing page(s) from master"
    run(["git", "commit", "-m", msg])
    run(["git", "push", "origin", "main"])
    print("✅ Commit + Push erledigt.")


if __name__ == "__main__":
    main()
