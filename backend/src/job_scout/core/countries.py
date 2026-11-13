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
    ),
}
