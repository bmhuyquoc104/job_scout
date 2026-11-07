import json
import re
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

FRONTEND_DIR = Path(__file__).resolve().parents[1]
CATEGORY_ID = "019a2bd1-7c00-7000-8000-000000000001"
JOB_ID = "019a2bd1-7c00-7000-8000-000000000002"
SECOND_JOB_ID = "019a2bd1-7c00-7000-8000-000000000003"
CLOSED_JOB_ID = "019a2bd1-7c00-7000-8000-000000000004"
SECOND_CATEGORY_ID = "019a2bd1-7c00-7000-8000-000000000009"


def test_dashboard_jobs_detail_and_back_navigation() -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen(
        [
            "pnpm",
            "dev",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--strictPort",
        ],
        cwd=FRONTEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 15
        while True:
            if server.poll() is not None:
                raise AssertionError("Vite exited before becoming ready")
            try:
                with urlopen(url, timeout=1):
                    break
            except URLError as error:
                if time.monotonic() >= deadline:
                    raise AssertionError("Vite did not become ready") from error
                time.sleep(0.1)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.route(
                "**/api/categories",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        [
                            {
                                "id": CATEGORY_ID,
                                "name": "Information & Communication Technology",
                                "slug": "ict",
                                "seek_classification_id": "6281",
                                "active_job_count": 1,
                            },
                            {
                                "id": SECOND_CATEGORY_ID,
                                "name": "Trades & Services",
                                "slug": "trades-services",
                                "seek_classification_id": "1225",
                                "active_job_count": 2,
                            },
                        ]
                    ),
                ),
            )

            def fulfill_jobs(route) -> None:
                query = parse_qs(urlparse(route.request.url).query)
                offset = int(query.get("offset", ["0"])[0])
                is_closed = query.get("status", ["open"])[0] == "closed"
                job_id, position = (
                    (CLOSED_JOB_ID, "Old Role")
                    if is_closed
                    else (JOB_ID, "Software Engineer")
                    if offset == 0
                    else (SECOND_JOB_ID, "Page Two Engineer")
                )
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "items": [
                                {
                                    "id": job_id,
                                    "source": "seek",
                                    "position": position,
                                    "company_name": "Example Co",
                                    "location": "Wellington",
                                    "work_arrangements": ["Hybrid"],
                                    "work_types": ["Full time"],
                                    "salary_label": "$100,000 per year",
                                    "pay_period": "Year",
                                    "annual_salary_min": 100000,
                                    "annual_salary_max": 100000,
                                    "listed_at": "2026-10-16T03:26:35Z",
                                    "is_active": not is_closed,
                                    "closed_at": "2026-10-30T00:00:00Z" if is_closed else None,
                                }
                            ],
                            "total": 1 if is_closed else 51,
                            "limit": 50,
                            "offset": offset,
                            "category_name": "Information & Communication Technology",
                            "category_slug": "ict",
                        }
                    ),
                )

            def fulfill_job(route) -> None:
                job_id = route.request.url.rsplit("/", 1)[1]
                position = "Software Engineer" if job_id == JOB_ID else "Page Two Engineer"
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "id": job_id,
                            "category_id": CATEGORY_ID,
                            "source": "seek",
                            "external_id": f"seek-{job_id}",
                            "company_name": "Example Co",
                            "location": "Wellington",
                            "work_arrangements": ["Hybrid"],
                            "work_types": ["Full time"],
                            "salary_label": "$100,000 per year",
                            "pay_period": "Year",
                            "annual_salary_min": 100000,
                            "annual_salary_max": 100000,
                            "position": position,
                            "job_description": "Full job description for the role.",
                            "url": f"https://www.seek.co.nz/job/seek-{job_id}",
                            "nzbn": "942903",
                            "trading_name": "Example Trading",
                            "listed_at": "2026-10-16T03:26:35Z",
                            "is_active": True,
                            "closed_at": None,
                        }
                    ),
                )

            levels = ["graduate", "junior", "mid", "senior", "lead", "management", "unspecified"]

            def trend_point(day: str, new: int, closed: int, senior: int, junior: int, other: int):
                counts = dict.fromkeys(levels, 0) | {
                    "senior": senior,
                    "junior": junior,
                    "unspecified": other,
                }
                return {
                    "date": day,
                    "total_open": sum(counts.values()),
                    "new": new,
                    "closed": closed,
                    "by_seniority": counts,
                }

            trends = {
                "points": [
                    trend_point("2026-10-30", 10, 0, 6, 0, 4),
                    trend_point("2026-10-31", 3, 1, 7, 1, 4),
                    trend_point("2026-11-01", 0, 1, 6, 1, 4),
                ],
                "seniority_levels": levels,
                "history_starts": "2026-10-30",
            }
            page.route(
                "**/api/categories/*/stats/trends**",
                lambda route: route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(trends)
                ),
            )
            locations = {
                "regions": [
                    {"region": "Auckland", "count": 6},
                    {"region": "Wellington", "count": 3},
                    {"region": "Canterbury", "count": 2},
                ],
                "total_open": 11,
            }
            page.route(
                "**/api/categories/*/stats/locations**",
                lambda route: route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(locations)
                ),
            )

            def green_role(role_id: str, title: str, tier: int, industry: str, **extra):
                return {
                    "id": role_id,
                    "title": title,
                    "anzsco_code": "261313",
                    "industry": industry,
                    "tier": tier,
                    "pathway": "Pathway line one.\n• Work for an accredited employer",
                    "requirements": "You must hold a recognised degree.",
                    "engineering_degrees": "",
                    "note": "",
                    "tier_changed_from": None,
                    "tier_changed_at": None,
                } | extra

            green_list = {
                "synced_at": "2026-11-06T15:12:25Z",
                "tier_1": 2,
                "tier_2": 1,
                "total": 3,
                "roles": [
                    green_role(
                        "g1",
                        "Nurse",
                        1,
                        "Health and social services",
                        tier_changed_from=2,
                        tier_changed_at="2026-11-03T03:00:00Z",
                    ),
                    green_role(
                        "g2", "Software Engineer", 1, "ICT, electronics and telecommunications"
                    ),
                    green_role("g3", "Welder", 2, "Trades"),
                ],
            }
            green_changes = {
                "changes": [
                    {
                        "occurred_at": "2026-11-03T03:00:00Z",
                        "event_type": "tier_changed",
                        "role_id": "g1",
                        "title": "Nurse",
                        "anzsco_code": "254499",
                        "industry": "Health",
                        "from_tier": 2,
                        "tier": 1,
                    },
                    {
                        "occurred_at": "2026-11-03T03:00:00Z",
                        "event_type": "removed",
                        "role_id": "g9",
                        "title": "Chef",
                        "anzsco_code": "351311",
                        "industry": "Trades",
                        "from_tier": None,
                        "tier": 2,
                    },
                ]
            }

            def json_response(body: dict):
                return lambda route: route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(body)
                )

            page.route("**/api/green-list", json_response(green_list))
            page.route("**/api/green-list/changes**", json_response(green_changes))
            page.route("**/api/categories/*/jobs**", fulfill_jobs)
            page.route("**/api/jobs/*", fulfill_job)

            page.goto(url)
            expect(page.get_by_role("heading", name="Job categories")).to_be_visible()
            expect(page.locator(".MuiTypography-root").first).to_be_visible()
            assert (
                page.locator("body").evaluate(
                    "element => getComputedStyle(element).backgroundColor"
                )
                == "rgb(30, 30, 46)"
            )
            assert (
                page.get_by_test_id("app-shell").evaluate(
                    "element => Math.round(element.getBoundingClientRect().height)"
                )
                == 900
            )
            page.get_by_role("link", name="View jobs").first.click()
            expect(page.get_by_role("heading", name="Accredited jobs")).to_be_visible()
            expect(page.get_by_role("columnheader", name="Position")).to_be_visible()
            # With several enabled categories the title area is a picker that keeps the same view.
            for destination in (SECOND_CATEGORY_ID, CATEGORY_ID):
                page.get_by_role("combobox", name="Category").click()
                name = "Trades & Services" if destination == SECOND_CATEGORY_ID else "Information"
                page.get_by_role("option", name=re.compile(name)).click()
                page.wait_for_url(re.compile(rf"/categories/{destination}$"))
            # The side nav switches between two separate views instead of one long page.
            expect(page.get_by_role("link", name="Job postings")).to_be_visible()
            expect(page.get_by_text("Open jobs now")).to_have_count(0)
            page.get_by_role("link", name="Diagrams").click()
            expect(page.get_by_role("heading", name="Diagrams")).to_be_visible()
            expect(page.get_by_role("columnheader", name="Position")).to_have_count(0)
            page.get_by_role("combobox", name="Category").click()
            page.get_by_role("option", name="Trades & Services").click()
            page.wait_for_url(re.compile(rf"/categories/{SECOND_CATEGORY_ID}/diagrams$"))
            page.get_by_role("combobox", name="Category").click()
            page.get_by_role("option", name=re.compile("Information")).click()
            page.wait_for_url(re.compile(rf"/categories/{CATEGORY_ID}/diagrams$"))
            # Trend charts: headline numbers come from the last day (6 + 1 + 4 = 11 open).
            expect(page.get_by_text("Open jobs now")).to_be_visible()
            expect(page.get_by_text("11", exact=True).first).to_be_visible()
            expect(page.get_by_text("History starts on")).to_be_visible()
            for chart in (
                "Open jobs",
                "New and closed",
                "Open jobs by seniority",
                "Jobs by location",
            ):
                expect(page.get_by_role("heading", name=chart, exact=True)).to_be_visible()
            # Wait for the closed dropdown (and its invisible backdrop) to go, or it eats the hover.
            expect(page.locator(".MuiPopover-root")).to_have_count(0)
            # Hovering a chart reads every series for that day; the table view lists every day.
            card = page.locator('section[aria-label="New and closed"]')
            box = card.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] - 90)
            tooltip = card.get_by_role("status")
            expect(tooltip).to_contain_text("New")
            expect(tooltip).to_contain_text("Closed")
            card.get_by_role("button", name="Table").click()
            expect(card.get_by_role("row")).to_have_count(4)  # header + 3 days
            page.mouse.move(0, 0)
            # Seniority pie: the legend carries every count and share; hovering a part reads it out.
            pie = page.locator('section[aria-label="Open jobs by seniority"]')
            legend = pie.get_by_role("list", name="Legend")
            expect(legend).to_contain_text("Senior")
            expect(legend).to_contain_text("Not stated")
            expect(pie.get_by_role("status")).to_contain_text("11 open jobs in total")
            legend.get_by_role("listitem").filter(has_text="Senior").hover()
            expect(pie.get_by_role("status")).to_contain_text("Senior: 6 jobs (55%)")
            # Location bars: ranked regions with value and share; the table lists the same rows.
            places = page.locator('section[aria-label="Jobs by location"]')
            expect(places.get_by_role("list", name="Jobs by location")).to_contain_text("Auckland")
            expect(places.get_by_role("listitem")).to_have_count(3)
            places.get_by_role("button", name="Table").click()
            expect(places.get_by_role("row")).to_have_count(4)  # header + 3 regions
            page.get_by_role("link", name="Job postings").click()
            expect(page.get_by_role("columnheader", name="Position")).to_be_visible()
            expect(page.get_by_text("Open jobs now")).to_have_count(0)
            assert (
                page.get_by_test_id("app-shell").evaluate(
                    "element => Math.round(element.getBoundingClientRect().height)"
                )
                == 900
            )
            expect(page.get_by_test_id("job-row").get_by_text("Open", exact=True)).to_be_visible()

            def open_column_menu(column: str) -> None:
                header = page.get_by_role("columnheader", name=column)
                header.hover()
                header.get_by_label("Menu").click()

            # Filters live in each column's menu; the active ones show as chips above the grid.
            open_column_menu("Status")
            page.get_by_role("radio", name="Closed").click()
            expect(page.get_by_role("link", name="Old Role")).to_be_visible()
            expect(page.get_by_test_id("job-row").get_by_text("Closed", exact=True)).to_be_visible()
            assert "status=closed" in page.url
            chips = page.get_by_role("list", name="Active filters")
            expect(chips).to_contain_text("Status: Closed")
            page.keyboard.press("Escape")  # close the menu
            chips.locator(".MuiChip-deleteIcon").click()  # removing the chip removes the filter
            expect(page.get_by_role("link", name="Software Engineer")).to_be_visible()
            assert "status" not in page.url
            expect(chips).to_have_count(0)
            # Sorting: the first click on a column sorts A to Z, the second flips it.
            page.get_by_role("columnheader", name="Position").click()
            page.wait_for_url(re.compile(r"sort=position&order=asc"))
            expect(page.get_by_role("columnheader", name="Position")).to_have_attribute(
                "aria-sort", "ascending"
            )
            page.get_by_role("columnheader", name="Position").click()
            expect(page.get_by_role("columnheader", name="Position")).to_have_attribute(
                "aria-sort", "descending"
            )
            assert "sort=position" in page.url and "order=" not in page.url  # desc is the default
            # Text filter: sent after typing stops, marks the column, and "Clear all" removes it.
            open_column_menu("Position")
            page.get_by_role("textbox", name="Position contains").fill("soft")
            page.wait_for_url(re.compile(r"position=soft"))
            page.keyboard.press("Escape")
            expect(page.get_by_role("list", name="Active filters")).to_contain_text("Position")
            expect(
                page.get_by_role("columnheader", name="Position").get_by_role(
                    "img", name="filtered"
                )
            ).to_be_visible()
            page.get_by_role("button", name="Clear all").click()
            page.wait_for_function("() => !location.search.includes('position=')")
            expect(page.get_by_role("list", name="Active filters")).to_have_count(0)
            page.get_by_role("button", name="Go to next page").click()
            expect(page.get_by_role("link", name="Page Two Engineer")).to_be_visible()
            expect(page.get_by_test_id("job-row")).to_contain_text("ago")
            page.get_by_role("link", name="Page Two Engineer").click()
            expect(page.get_by_role("heading", name="Page Two Engineer")).to_be_visible()
            expect(page.get_by_text("Full job description for the role.")).to_be_visible()
            expect(page.get_by_text("Example Trading")).to_be_visible()
            expect(page.locator("dl dt").filter(has_text="Salary")).to_be_visible()
            expect(page.get_by_text(re.compile(r"Listed .* ago"))).to_be_visible()
            page.get_by_role("link", name="Category jobs").click()
            expect(page.get_by_role("heading", name="Accredited jobs")).to_be_visible()
            expect(page.get_by_role("link", name="Page Two Engineer")).to_be_visible()
            assert "offset=50" in page.url
            page.go_back()
            expect(page.get_by_role("heading", name="Page Two Engineer")).to_be_visible()
            page.go_back()
            expect(page.get_by_role("heading", name="Accredited jobs")).to_be_visible()
            page.get_by_role("link", name="← Dashboard").click()
            expect(page.get_by_role("heading", name="Job categories")).to_be_visible()
            # Green List tab: tier options with counts, changes, search and a details dialog.
            page.get_by_role("link", name="Green List").click()
            expect(page.get_by_role("heading", name="Green List", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Tier 1 · 2")).to_be_visible()
            expect(page.get_by_role("button", name="Tier 2 · 1")).to_be_visible()
            expect(page.get_by_role("button", name="All · 3")).to_be_visible()
            changes = page.get_by_role("region", name="Recent changes")
            expect(changes).to_contain_text("Nurse: Tier 2 → Tier 1")
            expect(changes).to_contain_text("Chef removed from the list")
            expect(page.get_by_role("gridcell", name="Welder")).to_be_visible()
            page.get_by_role("button", name="Tier 1 · 2").click()
            expect(page.get_by_role("gridcell", name="Nurse")).to_be_visible()
            expect(page.get_by_role("gridcell", name="Welder")).to_have_count(0)
            expect(page.get_by_text("was 2")).to_be_visible()  # Nurse moved up from Tier 2
            page.get_by_role("textbox", name="Search roles").fill("software")
            expect(page.get_by_role("gridcell", name="Nurse")).to_have_count(0)
            page.get_by_role("gridcell", name="Software Engineer").click()
            dialog = page.get_by_role("dialog")
            expect(dialog).to_contain_text("You must hold a recognised degree.")
            expect(dialog).to_contain_text("Work for an accredited employer")
            dialog.get_by_role("button", name="Close").click()
            expect(page.get_by_role("dialog")).to_have_count(0)
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
