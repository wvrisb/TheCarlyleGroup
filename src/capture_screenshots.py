"""Re-capture the tab screenshots in docs/screenshots/ from dashboard/index.html (default filters)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TABS = [("summary", "1_summary"), ("happened", "2_happened"), ("outcomes", "3_outcomes"),
        ("learn", "4_learn"), ("firms", "5_firms"), ("methods", "6_methods")]

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1.5)
    pg.goto((ROOT / "dashboard/index.html").as_uri())
    for tab, name in TABS:
        pg.click(f'button[data-tab="{tab}"]')
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(ROOT / f"docs/screenshots/{name}.png"), full_page=True)
        print("saved", name)
    b.close()
