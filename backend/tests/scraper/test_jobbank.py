from datetime import UTC, datetime

from job_scout.scraper import jobbank


def article(job_id: str, title: str, salary: str = "", flag: str = "") -> str:
    """One result, shaped like Job Bank's search page."""
    pay = f'<li class="salary"><span class="fa"></span> Salary {salary}</li>' if salary else ""
    return (
        f'<article id="article-{job_id}" class="action-buttons">'
        f'<a href="/jobsearch/jobposting/{job_id};jsessionid=X?source=searchresults">'
        f'<h3 class="title"><span class="flag"><span class="new"> New </span>{flag}</span>'
        f'<span class="noctitle"> {title} </span></h3><ul class="list-unstyled">'
        '<li class="date">November 14, 2026</li><li class="business">Nord Quantique</li>'
        '<li class="location"><span class="wb-inv">Location</span> Sherbrooke (QC) </li>'
        f"{pay}</ul></a></article>"
    )


REQUESTED = (
    '<span class="jobLMIAflag submitted nopopup">LMIA requested</span><input value="submited"/>'
)
# shortcut: the approved markup is inferred from the page's script (not seen live); recheck if
# approved jobs are ever missing their note.
APPROVED = (
    '<span class="jobLMIAflag approved nopopup">LMIA approved</span><input value="approved"/>'
)


def test_a_search_page_gives_each_job_its_fields_and_lmia_status() -> None:
    page = article("1", "application architect", "$123,000.00 to $140,000.00 annually", REQUESTED)
    page += article("2", "web developer")

    first, second = jobbank.parse_search_page(page)

    assert first == {
        "id": "1",
        "title": "application architect",
        "company": "Nord Quantique",
        "location": "Sherbrooke (QC)",
        "salary": "$123,000.00 to $140,000.00 annually",
        "posted": "November 14, 2026",
        "lmia": "requested",
        "url": "https://www.jobbank.gc.ca/jobsearch/jobposting/1",
    }
    assert (second["salary"], second["lmia"]) == ("", "")


def test_a_job_page_gives_its_description_text() -> None:
    page = (
        '<h2>Job details</h2><span class="hidden" property="description">'
        "Tasks: Write code. Test it.</span>"
    )

    assert jobbank.parse_description(page) == "Tasks: Write code. Test it."
    assert jobbank.parse_description("<p>nothing here</p>") == ""
    escaped = (
        '<span class="hidden" property="description">'
        "&lt;p&gt;Build &lt;b&gt;APIs&lt;/b&gt;&lt;/p&gt;</span>"
    )
    assert jobbank.parse_description(escaped) == "Build APIs"


def test_a_listing_is_normalised_with_its_lmia_status_in_the_description() -> None:
    payload = {
        **jobbank.parse_search_page(article("7", "web developer", "$60,000.00 annually", APPROVED))[
            0
        ],
        "description": "Tasks: Build sites.",
    }

    listing = jobbank.normalize_listing(payload)

    assert (listing.source, listing.external_id, listing.company_name) == (
        "jobbank",
        "7",
        "Nord Quantique",
    )
    assert (listing.salary_label, listing.pay_period) == ("$60,000.00 per year", "Year")
    assert listing.listed_at == datetime(2026, 11, 14, tzinfo=UTC)
    assert jobbank.build_description(payload) == (
        "Tasks: Build sites.\n\nThe employer has an approved LMIA (can hire foreign workers)."
    )


def test_a_job_with_no_description_still_gets_a_pointer_to_the_original_listing() -> None:
    payload = {"url": "https://www.jobbank.gc.ca/jobsearch/jobposting/9", "description": ""}

    assert jobbank.build_description(payload) == (
        "Job Bank has no description for this job; see the original listing: "
        "https://www.jobbank.gc.ca/jobsearch/jobposting/9"
    )
