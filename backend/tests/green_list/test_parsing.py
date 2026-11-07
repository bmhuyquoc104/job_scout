import pytest

from job_scout.core.errors import AppError, ErrorCode
from job_scout.green_list.parsing import html_to_text, parse_record
from tests.green_list.conftest import TIER_1, TIER_2, inz_record


def test_parse_record_reads_the_role_fields() -> None:
    role = parse_record(inz_record(record_id="195472", title="Software Engineer"))

    assert role.record_id == "195472"
    assert role.title == "Software Engineer"
    assert role.anzsco_code == "261313"
    assert role.industry == "ICT, electronics and telecommunications"
    assert role.tier == 1
    assert role.pathway == "To be eligible you must be:\n• working here"
    assert role.requirements == "You must have one of the following:\n• A degree.\n• Or a diploma."
    assert role.note == ""  # the site writes "None" when there is no note
    assert role.raw["record_id"] == {"raw": "195472"}


def test_parse_record_reads_tier_two_and_a_real_note() -> None:
    role = parse_record(inz_record(tier=TIER_2, note="Registration required."))

    assert (role.tier, role.note) == (2, "Registration required.")


def test_html_to_text_keeps_lists_and_drops_markup_and_scripts() -> None:
    html = (
        "<p>Needs &amp; wants:</p>\n<ul><li>one <b>bold</b></li><li>two</li></ul>"
        "<script>alert('x')</script><style>p{}</style><p>Done.</p>"
    )

    assert html_to_text(html) == "Needs & wants:\n• one bold\n• two\nDone."
    assert html_to_text("") == ""
    assert "<" not in html_to_text("<div><span>a</span> <i>b</i></div><br>c")


def test_a_record_without_a_tier_is_rejected_instead_of_guessed() -> None:
    with pytest.raises(AppError) as error:
        parse_record(inz_record(tier="Not a tier"))

    assert error.value.code is ErrorCode.SCRAPE_SOURCE_ERROR


def test_a_record_without_an_id_is_rejected() -> None:
    record = inz_record()
    del record["record_id"]

    with pytest.raises(AppError):
        parse_record(record)


def test_tier_is_found_whatever_the_column_is_called() -> None:
    assert parse_record(inz_record(anzsco=" ANZSCO 999999", tier=TIER_1)).tier == 1
