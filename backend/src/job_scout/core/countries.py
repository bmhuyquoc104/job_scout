"""The one list of countries the app covers.

Adding a country = add it here, add a migration that inserts its categories, and give it an
employer check in scraper/enrichment.py if its immigration rules have one.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    name: str
    seek_host: str
    seek_site_key: str
    seek_locale: str
    indeed_host: str
    glassdoor_host: str
    search_place: str  # what the job boards' location search is given for the whole country
    immigration_body: str  # who publishes the priority-occupation list
    occupation_list_name: str  # what that list is called
    # NZ only so far: Immigration NZ's accredited employer list. Other countries promote every
    # listing until their own check exists (e.g. Australia's approved sponsor register).
    employer_check: bool
    currency: str = "$"  # symbol used in the salary labels the job boards build
    # shortcut: hand-written one-liners on the main routes that apply to any job, not scraped;
    # recheck them against the official sites when rules change.
    general_routes: tuple[str, ...] = ()


COUNTRIES: dict[str, Country] = {
    "NZ": Country(
        "New Zealand",
        "www.seek.co.nz",
        "NZ-Main",
        "en-NZ",
        "nz.indeed.com",
        "www.glassdoor.co.nz",
        "New Zealand",
        "Immigration New Zealand",
        "Green List",
        employer_check=True,
        general_routes=(
            "Accredited Employer Work Visa: a job offer from an accredited employer.",
            "Skilled Migrant Category residence: points-based, with or without a Green List role.",
        ),
    ),
    "AU": Country(
        "Australia",
        "www.seek.com.au",
        "AU-Main",
        "en-AU",
        "au.indeed.com",
        "www.glassdoor.com.au",
        "Australia",
        "Department of Home Affairs",
        "Skilled occupation lists",
        employer_check=False,
        general_routes=(
            "Skills in Demand visa (482): employer-sponsored work visa.",
            "Skilled Independent (189) and Nominated (190) visas: points-tested, for roles on the "
            "long-term lists.",
        ),
    ),
    # No SEEK in Canada (empty seek fields): the job boards are Indeed, Glassdoor and Job Bank.
    "CA": Country(
        "Canada",
        "",
        "",
        "en-CA",
        "ca.indeed.com",
        "www.glassdoor.ca",
        "Canada",
        "Immigration, Refugees and Citizenship Canada",
        "Express Entry categories",
        employer_check=False,
        general_routes=(
            "Express Entry general draws: ranked by points; an LMIA-backed job offer adds points.",
            "Employer-specific work permit: needs an LMIA for the job.",
        ),
    ),
    # No SEEK here either. The rule is a salary threshold (EU Blue Card), not an occupation list.
    "DE": Country(
        "Germany",
        "",
        "",
        "de-DE",
        "de.indeed.com",
        "www.glassdoor.de",
        "Germany",
        "Federal Employment Agency",
        "EU Blue Card salary thresholds",
        employer_check=False,
        general_routes=(
            "EU Blue Card: a job offer at the minimum salary (see the thresholds below).",
            "Opportunity Card (Chancenkarte): points-based visa to look for work.",
            "Skilled worker visa: a recognised qualification and a job offer.",
        ),
        currency="€",
    ),
}
