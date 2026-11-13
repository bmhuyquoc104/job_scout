from job_scout.matching.skills import find_skills


def test_find_skills_reads_symbols_aliases_and_phrases() -> None:
    text = "C++, C# and Node.js; k8s on Microsoft Azure; machine learning, Power BI, Postgres."

    assert find_skills(text) == {
        "c++", "c#", "node.js", "kubernetes", "azure", "machine-learning", "power-bi", "postgresql",
    }  # fmt: skip


def test_find_skills_ignores_names_inside_longer_words() -> None:
    # "java" in "javascript", "sql" in "mysql" and the verb "go" are not those skills.
    assert find_skills("JavaScript and MySQL; ready to go") == {"javascript", "mysql"}
