from importlib.metadata import entry_points


def test_backend_console_command_targets_dev_server() -> None:
    script = next(
        (
            item
            for item in entry_points(group="console_scripts")
            if item.name == "job_scout_backend"
        ),
        None,
    )

    assert script is not None
    assert script.value == "job_scout.main:run_dev_server"


def test_scraper_console_command_targets_existing_cli() -> None:
    script = next(
        (item for item in entry_points(group="console_scripts") if item.name == "job_scout_scrape"),
        None,
    )

    assert script is not None
    assert script.value == "job_scout.scraper.main:main"


def test_dev_server_runs_fastapi_with_reload(monkeypatch) -> None:
    from job_scout import main

    calls = []
    monkeypatch.setattr(main.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    main.run_dev_server()

    assert calls == [(("job_scout.main:app",), {"reload": True})]


def test_openapi_command_prints_the_api_schema_the_frontend_types_come_from(capsys) -> None:
    import json

    from job_scout import main

    main.print_openapi()

    schemas = json.loads(capsys.readouterr().out)["components"]["schemas"]
    assert {"CategoryItem", "PaginatedJobs", "JobDetail"} <= set(schemas)
    assert "category_name" in schemas["PaginatedJobs"]["properties"]
