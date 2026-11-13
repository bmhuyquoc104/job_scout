# Graph Report - jobs  (2026-11-14)

## Corpus Check
- 154 files · ~44,884 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 8, .example 1, .ini 1)

## Summary
- 1259 nodes · 3459 edges · 69 communities (54 shown, 15 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 439 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ada493e2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_main.py
- asyncio
- Category
- enrichment.py
- test_migrations.py
- Category
- ColumnFilterForm.tsx
- package.json
- test_seek_client.py
- compilerOptions
- test_discovery.py
- job-scout
- sqlalchemy
- test_enrichment.py
- green_list/service.py
- TrendsPanel.tsx
- Project guidance
- useApi
- ErrorCode
- client.ts
- exception_handlers.py
- Jobs.tsx
- schema.d.ts
- jobs/models.py
- test_job_events.py
- test_employmenthero.py
- source_listing
- test_scrape_commits_draft_before_enrichment_and_upserts_clean_job
- Job Scout
- devDependencies
- re
- AppError
- test_job_boards.py
- matching/service.py
- categories/service.py
- configure_logging
- AppError
- discovery.py
- parse_record
- make_job
- test_client.py
- vercel.json
- glassdoor.py
- green_db
- indeed.py
- test_sync.py
- env.py
- CvUpload.tsx
- employmenthero.py
- scrape_one
- sync.py
- dependencies
- JobDraft
- scripts
- eslint.config.js
- httpx
- test_seek_client_description.py
- test_matching.py
- 2026-11-07_allow_indeed_glassdoor_sources.py
- test_api.py
- vite.config.ts
- engines

## God Nodes (most connected - your core abstractions)
1. `AppError` - 102 edges
2. `ErrorCode` - 76 edges
3. `Job` - 69 edges
4. `Category` - 62 edges
5. `source_listing()` - 48 edges
6. `JobDraft` - 33 edges
7. `configure_logging()` - 26 edges
8. `@mui/material` - 24 edges
9. `apply_sync()` - 23 edges
10. `run()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `discover()` --calls--> `discover_phase()`  [INFERRED]
  airflow/dags/employmenthero_sync.py → backend/src/job_scout/scraper/phases.py
- `reconcile()` --calls--> `reconcile_phase()`  [INFERRED]
  airflow/dags/employmenthero_sync.py → backend/src/job_scout/scraper/phases.py
- `enrich()` --calls--> `enrich_phase()`  [INFERRED]
  airflow/dags/employmenthero_sync.py → backend/src/job_scout/scraper/phases.py
- `sync_green_list()` --calls--> `run()`  [INFERRED]
  airflow/dags/green_list_sync.py → backend/src/job_scout/scraper/runner.py
- `discover()` --calls--> `discover_phase()`  [INFERRED]
  airflow/dags/job_board_sync.py → backend/src/job_scout/scraper/phases.py

## Import Cycles
- None detected.

## Communities (69 total, 15 thin omitted)

### Community 0 - "test_main.py"
Cohesion: 0.10
Nodes (17): _Session, test_command_accepts_the_job_board_sources(), test_command_configures_shared_logging(), complete(), test_command_exits_nonzero_when_scrape_fails(), fail(), test_discover_phase_prints_scan_timestamp(), test_enrich_phase_returns_failure_when_drafts_remain_failed() (+9 more)

### Community 1 - "asyncio"
Cohesion: 0.31
Nodes (3): backfill(), main(), fetch_description()

### Community 2 - "Category"
Cohesion: 0.08
Nodes (35): Category, list_categories(), Job, api_context(), test_categories_returns_enabled_category_with_active_job_count(), _list(), _positions(), test_arrangement_and_work_type_filters_match_any_selected_value() (+27 more)

### Community 3 - "enrichment.py"
Cohesion: 0.22
Nodes (6): enrich(), _full_seek_description(), process_listing(), build_description(), normalize_listing(), normalize_text()

### Community 4 - "test_migrations.py"
Cohesion: 0.05
Nodes (27): Settings, async_test_database_url(), postgres_url(), sync_test_database_url(), connection(), test_every_seek_classification_is_seeded_and_only_ict_is_enabled(), test_green_list_tables_exist_and_events_follow_their_role(), test_job_event_table_records_job_history_and_follows_its_job() (+19 more)

### Community 5 - "Category"
Cohesion: 0.06
Nodes (37): require_enabled_category(), build_location_breakdown(), get_location_breakdown(), get_category_job_facets(), get_category_jobs(), get_category_locations(), get_category_sources(), get_category_trends() (+29 more)

### Community 6 - "ColumnFilterForm.tsx"
Cohesion: 0.11
Nodes (29): JobListItem, sourceLabel(), clearAllFilters(), clearFilter(), describeFilter(), FIELD_LABELS, FILTER_FIELDS, FilterField (+21 more)

### Community 7 - "package.json"
Cohesion: 0.14
Nodes (13): name, packageManager, private, type, version, @emotion/react, @emotion/styled, eslint (+5 more)

### Community 8 - "test_seek_client.py"
Cohesion: 0.11
Nodes (12): app_error_probe(), client(), _fetch_with_responses(), fake_sleep(), test_fetch_search_page_does_not_retry_client_errors(), test_fetch_search_page_follows_seek_market_redirect(), test_fetch_search_page_gives_up_after_three_attempts(), test_fetch_search_page_rejects_non_object_payload_with_central_error() (+4 more)

### Community 10 - "compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+8 more)

### Community 11 - "test_discovery.py"
Cohesion: 0.15
Nodes (17): test_changed_payload_resets_attempts_and_makes_a_draft_pending_again(), fetch_page(), test_discovery_logs_which_response_check_failed(), test_discovery_persists_pending_drafts_without_enrichment(), fetch_page(), test_drafts_are_saved_once_per_seek_page(), fetch_page(), test_pagination_continues_until_seek_returns_zero_total_count() (+9 more)

### Community 16 - "sqlalchemy"
Cohesion: 0.12
Nodes (8): upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade()

### Community 17 - "test_enrichment.py"
Cohesion: 0.21
Nodes (15): _seed_pending(), test_accredited_job_description_comes_from_the_search_result(), test_accredited_listing_without_any_description_is_recorded_as_failed(), test_accredited_seek_job_gets_the_full_description(), test_app_error_keeps_its_own_code_when_recorded_on_the_draft(), test_drafts_that_exhausted_their_attempts_are_not_retried(), test_enrichment_retries_failed_drafts_but_skips_completed_drafts(), test_failed_enrichment_increments_attempts() (+7 more)

### Community 18 - "green_list/service.py"
Cohesion: 0.23
Nodes (8): get_green_list(), get_green_list_changes(), GreenListChange, GreenListChangesResponse, GreenListResponse, GreenListRoleItem, get_changes(), get_green_list()

### Community 19 - "TrendsPanel.tsx"
Cohesion: 0.12
Nodes (31): ChartCard(), ChartCardProps, ChartShell(), ChartShellProps, ChartTable(), ChartTableProps, BarItem, HorizontalBarChart() (+23 more)

### Community 20 - "Project guidance"
Cohesion: 0.25
Nodes (7): Agent and model selection, Async and data, Errors and exceptions, graphify, Monorepo, Project guidance, Quality checks

### Community 21 - "useApi"
Cohesion: 0.16
Nodes (22): getCategories(), getJob(), loadSources(), Settled, useApi(), App(), CategorySwitcher(), CategorySwitcherProps (+14 more)

### Community 22 - "ErrorCode"
Cohesion: 0.12
Nodes (14): ErrorCode, ErrorDefinition, check_accreditation(), extract_immigration_fields(), is_accredited(), StubPage, test_accreditation_rule_preserves_current_non_no_results_behavior(), test_check_accreditation_raises_after_three_failures() (+6 more)

### Community 23 - "client.ts"
Cohesion: 0.10
Nodes (29): ApiError, CategoryItem, CvSkills, get(), getGreenList(), getGreenListChanges(), getLocations(), getSources() (+21 more)

### Community 24 - "exception_handlers.py"
Cohesion: 0.15
Nodes (11): app_error_handler(), error_response(), http_error_handler(), register_exception_handlers(), unexpected_error_handler(), validation_error_handler(), test_application_error_uses_catalog_status_and_message(), test_error_detail_is_never_sent_to_clients() (+3 more)

### Community 26 - "Jobs.tsx"
Cohesion: 0.12
Nodes (27): getCategoryJobs(), getJobFacets(), JobFacets, JobSource, JobStatus, SOURCE_LABELS, DEFAULT_PARAMS, hasActiveFilters() (+19 more)

### Community 27 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 30 - "test_job_events.py"
Cohesion: 0.49
Nodes (10): enriched(), events_for(), promote(), test_changed_fields_are_recorded_as_an_updated_event(), test_promoting_a_new_job_records_a_new_event(), test_promoting_an_inactive_job_records_reopened(), test_promoting_unchanged_data_again_records_nothing(), test_promotion_stores_the_parsed_annual_salary() (+2 more)

### Community 31 - "test_employmenthero.py"
Cohesion: 0.16
Nodes (17): eh_site(), fetch_job(), job_page(), list_page(), test_a_seek_draft_with_the_same_id_does_not_count_as_seen_for_employment_hero(), test_build_description_turns_html_into_readable_text(), test_discovery_fails_closed_when_a_job_page_cannot_be_read(), test_discovery_fails_closed_when_the_first_page_has_no_jobs() (+9 more)

### Community 32 - "source_listing"
Cohesion: 0.23
Nodes (8): source_listing(), test_bad_immigration_payload_is_recorded_and_does_not_overwrite_job(), fetch_page(), test_exhausted_accreditation_retries_are_recorded_as_failure(), fetch_page(), test_non_accredited_result_preserves_existing_clean_job(), fetch_page(), fetch_page()

### Community 33 - "test_scrape_commits_draft_before_enrichment_and_upserts_clean_job"
Cohesion: 0.23
Nodes (4): test_run_does_not_count_exhausted_drafts_as_new_failures(), fetch_page(), test_scrape_commits_draft_before_enrichment_and_upserts_clean_job(), fetch_page()

### Community 35 - "devDependencies"
Cohesion: 0.17
Nodes (12): devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, globals, openapi-typescript, @types/react, @types/react-dom (+4 more)

### Community 36 - "re"
Cohesion: 0.29
Nodes (5): downgrade(), slugify(), upgrade(), test_database_check_allows_exactly_the_declared_sources(), test_every_declared_source_can_be_scraped_and_enriched()

### Community 38 - "AppError"
Cohesion: 0.14
Nodes (8): AppError, fetch_search_page(), parse_search_page(), SearchPage, test_app_error_exposes_catalog_message_and_keeps_detail_for_logs(), accreditation(), accreditation(), blocked()

### Community 39 - "test_job_boards.py"
Cohesion: 0.12
Nodes (8): fake_pages(), pages_gen(), no_real_clients(), _NoClient, test_discovery_fails_closed_when_a_page_cannot_be_read(), test_discovery_fails_closed_when_the_first_page_has_no_jobs(), test_discovery_saves_drafts_for_every_listed_job(), test_indeed_parse_search_without_job_search_is_a_source_error()

### Community 40 - "matching/service.py"
Cohesion: 0.08
Nodes (14): get_session(), match_cv(), read_cv(), CvSkills, JobMatch, MatchRequest, match_jobs(), parse_cv() (+6 more)

### Community 42 - "configure_logging"
Cohesion: 0.07
Nodes (31): job_scout_employmenthero_daily(), discover(), enabled_categories(), enrich(), reconcile(), sync(), job_scout_green_list_monthly(), sync_green_list() (+23 more)

### Community 43 - "AppError"
Cohesion: 0.24
Nodes (9): main(), run_once(), _category_id(), discover_phase(), enrich_phase(), reconcile_phase(), run_all_phases(), run() (+1 more)

### Community 44 - "discovery.py"
Cohesion: 0.13
Nodes (16): JobEvent, JobEventType, discover(), discover_employmenthero(), discover_job_board(), discoverer(), DiscoverySummary, reconcile_active_jobs() (+8 more)

### Community 45 - "parse_record"
Cohesion: 0.14
Nodes (11): html_to_text(), parse_record(), _raw(), _TextExtractor, inz_record(), test_a_record_without_a_tier_is_rejected_instead_of_guessed(), test_a_record_without_an_id_is_rejected(), test_html_to_text_keeps_lists_and_drops_markup_and_scripts() (+3 more)

### Community 46 - "make_job"
Cohesion: 0.27
Nodes (3): make_job(), test_empty_complete_scrape_marks_jobs_inactive_without_deleting_them(), test_reconcile_reactivates_seen_jobs_and_inactivates_absent_jobs()

### Community 47 - "test_client.py"
Cohesion: 0.20
Nodes (8): fetch(), response(), test_a_non_json_answer_is_refused(), test_an_incomplete_or_odd_response_is_refused(), test_fetch_sends_the_green_list_query_and_parses_every_role(), handler(), test_transient_server_errors_are_retried_then_given_up(), flaky()

### Community 49 - "glassdoor.py"
Cohesion: 0.17
Nodes (9): client(), request(), build_description(), client(), _descriptions(), _graph(), pages(), parse_listing() (+1 more)

### Community 50 - "green_db"
Cohesion: 0.36
Nodes (3): green_api(), override_session(), green_db()

### Community 51 - "indeed.py"
Cohesion: 0.22
Nodes (10): normalize_listing(), build_description(), build_query(), client(), normalize_listing(), pages(), parse_search(), _salary_label() (+2 more)

### Community 52 - "test_sync.py"
Cohesion: 0.46
Nodes (10): GreenListRole, events(), roles(), test_a_removed_role_stays_in_the_table_as_inactive(), test_a_tier_change_is_recorded_with_old_and_new_tier(), test_an_empty_or_collapsed_list_never_removes_anything(), test_new_removed_and_restored_roles_are_recorded(), test_syncing_unchanged_data_records_nothing() (+2 more)

### Community 53 - "env.py"
Cohesion: 0.28
Nodes (4): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online()

### Community 54 - "CvUpload.tsx"
Cohesion: 0.17
Nodes (17): getMatches(), JobMatch, uploadCv(), CvUpload(), onDrop(), upload(), STEPS, JobRow() (+9 more)

### Community 55 - "employmenthero.py"
Cohesion: 0.20
Nodes (10): build_description(), client(), fetch_job_page(), fetch_list_page(), _get(), job_url(), normalize_listing(), parse_job_posting() (+2 more)

### Community 57 - "sync.py"
Cohesion: 0.16
Nodes (9): fetch_green_list(), main(), GreenListEvent, GreenListEventType, RoleRecord, apply_sync(), _content(), sync_green_list() (+1 more)

### Community 58 - "dependencies"
Cohesion: 0.25
Nodes (8): dependencies, @emotion/react, @emotion/styled, @mui/material, @mui/x-data-grid, react, react-dom, react-router-dom

### Community 59 - "JobDraft"
Cohesion: 0.53
Nodes (3): JobDraft, _status(), test_noisy_seek_fields_do_not_reset_a_completed_draft()

### Community 60 - "scripts"
Cohesion: 0.33
Nodes (6): scripts, build, dev, gen:api, lint, preview

### Community 61 - "eslint.config.js"
Cohesion: 0.40
Nodes (4): @eslint/js, eslint-plugin-react-hooks, globals, typescript-eslint

### Community 62 - "httpx"
Cohesion: 0.47
Nodes (3): _Meta, _Page, _Response

### Community 63 - "test_seek_client_description.py"
Cohesion: 0.33
Nodes (4): _Http, _Response, test_fetch_description_is_none_when_seek_has_no_job(), test_fetch_description_turns_html_into_text()

### Community 64 - "test_matching.py"
Cohesion: 0.32
Nodes (8): make_pdf(), match_client(), test_cv_upload_returns_its_distinct_words(), test_cv_without_any_it_skill_is_rejected(), test_every_open_job_is_ranked_with_skills_to_add_for_weak_matches(), test_non_pdf_upload_is_rejected(), test_pdf_without_text_is_rejected(), upload()

### Community 65 - "2026-11-07_allow_indeed_glassdoor_sources.py"
Cohesion: 0.83
Nodes (3): downgrade(), _swap(), upgrade()

### Community 66 - "test_api.py"
Cohesion: 0.47
Nodes (6): roles(), test_a_role_that_changed_tier_says_so_and_a_removed_one_is_hidden(), test_an_empty_table_returns_zeros(), test_changes_list_newest_first_with_what_changed(), test_changes_validate_the_period(), test_roles_come_with_tier_counts_sorted_by_title()

## Knowledge Gaps
- **8 isolated node(s):** `job-scout`, `@emotion/react`, `@emotion/styled`, `@types/react`, `@types/react-dom` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 379 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppError` connect `AppError` to `test_main.py`, `asyncio`, `enrichment.py`, `test_migrations.py`, `Category`, `test_seek_client.py`, `test_discovery.py`, `test_enrichment.py`, `ErrorCode`, `exception_handlers.py`, `test_employmenthero.py`, `source_listing`, `test_job_boards.py`, `matching/service.py`, `categories/service.py`, `configure_logging`, `AppError`, `discovery.py`, `parse_record`, `test_client.py`, `glassdoor.py`, `indeed.py`, `test_sync.py`, `employmenthero.py`, `sync.py`, `httpx`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `AppError` (e.g. with `app_error_handler()` and `register_exception_handlers()`) actually correct?**
  _`AppError` has 44 INFERRED edges - model-reasoned connections that need verification._
- **What connects `job-scout`, `@emotion/react`, `@emotion/styled` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10080645161290322 - nodes in this community are weakly interconnected._
- **Why does `Job` connect `Category` to `test_matching.py`, `asyncio`, `source_listing`, `test_scrape_commits_draft_before_enrichment_and_upserts_clean_job`, `Category`, `matching/service.py`, `categories/service.py`, `test_discovery.py`, `discovery.py`, `make_job`, `scrape_one`, `jobs/models.py`, `test_job_events.py`, `test_employmenthero.py`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `ErrorCode` (e.g. with `require_enabled_category()` and `error_response()`) actually correct?**
  _`ErrorCode` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Should `Category` be split into smaller, more focused modules?**
  _Cohesion score 0.07923497267759563 - nodes in this community are weakly interconnected._