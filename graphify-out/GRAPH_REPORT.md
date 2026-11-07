# Graph Report - jobs  (2026-11-08)

## Corpus Check
- 142 files · ~41,089 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 8, .example 1, .ini 1)

## Summary
- 1166 nodes · 3167 edges · 61 communities (47 shown, 14 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 415 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4fb81c8b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_main.py
- test_immigration_client.py
- Category
- sqlalchemy
- test_migrations.py
- Category
- ColumnFilterForm.tsx
- package.json
- test_seek_client.py
- compilerOptions
- source_listing
- job-scout
- apply_sync
- jobs/models.py
- green_list/service.py
- TrendsPanel.tsx
- Project guidance
- useApi
- test_normalization.py
- client.ts
- AppError
- Jobs.tsx
- schema.d.ts
- configure_logging
- test_job_events.py
- test_employmenthero.py
- normalization.py
- jobColumns.tsx
- Job Scout
- phases.py
- green_db
- test_job_boards.py
- parse_record
- discovery.py
- test_api.py
- employmenthero.py
- test_errors.py
- errors.py
- persistence.py
- categories/service.py
- vercel.json
- glassdoor.py
- inz_record
- _TextExtractor
- indeed.py
- devDependencies
- re
- test_phases.py
- dependencies
- scripts
- eslint.config.js
- vite.config.ts
- engines

## God Nodes (most connected - your core abstractions)
1. `AppError` - 94 edges
2. `ErrorCode` - 73 edges
3. `Job` - 64 edges
4. `Category` - 61 edges
5. `source_listing()` - 44 edges
6. `JobDraft` - 31 edges
7. `configure_logging()` - 24 edges
8. `apply_sync()` - 23 edges
9. `@mui/material` - 22 edges
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

## Communities (61 total, 14 thin omitted)

### Community 0 - "test_main.py"
Cohesion: 0.10
Nodes (15): _Session, test_command_configures_shared_logging(), test_command_exits_nonzero_when_scrape_fails(), fail(), test_discover_phase_prints_scan_timestamp(), test_enrich_phase_returns_failure_when_drafts_remain_failed(), test_full_run_exits_nonzero_when_listings_failed(), run_all() (+7 more)

### Community 1 - "test_immigration_client.py"
Cohesion: 0.11
Nodes (13): process_listing(), check_accreditation(), extract_immigration_fields(), is_accredited(), StubPage, test_accreditation_rule_preserves_current_non_no_results_behavior(), test_check_accreditation_raises_after_three_failures(), test_check_accreditation_reloads_the_page_when_a_lookup_fails() (+5 more)

### Community 2 - "Category"
Cohesion: 0.09
Nodes (34): Category, Job, api_context(), test_categories_returns_enabled_category_with_active_job_count(), _list(), _positions(), test_arrangement_and_work_type_filters_match_any_selected_value(), test_bad_sort_and_filter_values_are_validation_errors() (+26 more)

### Community 3 - "sqlalchemy"
Cohesion: 0.13
Nodes (9): upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade(), downgrade(), _swap() (+1 more)

### Community 4 - "test_migrations.py"
Cohesion: 0.06
Nodes (18): Settings, async_test_database_url(), postgres_url(), sync_test_database_url(), connection(), test_every_seek_classification_is_seeded_and_only_ict_is_enabled(), test_green_list_tables_exist_and_events_follow_their_role(), test_job_event_table_records_job_history_and_follows_its_job() (+10 more)

### Community 5 - "Category"
Cohesion: 0.07
Nodes (36): require_enabled_category(), build_location_breakdown(), get_location_breakdown(), get_category_job_facets(), get_category_jobs(), get_category_locations(), get_category_sources(), get_category_trends() (+28 more)

### Community 6 - "ColumnFilterForm.tsx"
Cohesion: 0.14
Nodes (24): SOURCE_LABELS, clearAllFilters(), clearFilter(), describeFilter(), FIELD_LABELS, FILTER_FIELDS, FilterField, isFilterActive() (+16 more)

### Community 7 - "package.json"
Cohesion: 0.14
Nodes (13): name, packageManager, private, type, version, @emotion/react, @emotion/styled, eslint (+5 more)

### Community 8 - "test_seek_client.py"
Cohesion: 0.13
Nodes (9): client(), _fetch_with_responses(), fake_sleep(), test_fetch_search_page_does_not_retry_client_errors(), test_fetch_search_page_follows_seek_market_redirect(), test_fetch_search_page_gives_up_after_three_attempts(), test_fetch_search_page_retries_transient_server_errors_with_backoff(), test_fetch_search_page_sends_category_and_pagination_parameters() (+1 more)

### Community 10 - "compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+8 more)

### Community 11 - "source_listing"
Cohesion: 0.05
Nodes (49): JobDraft, make_job(), scrape_one(), source_listing(), test_changed_payload_resets_attempts_and_makes_a_draft_pending_again(), fetch_page(), test_discovery_logs_which_response_check_failed(), test_discovery_persists_pending_drafts_without_enrichment() (+41 more)

### Community 16 - "apply_sync"
Cohesion: 0.43
Nodes (11): GreenListRole, apply_sync(), events(), roles(), test_a_removed_role_stays_in_the_table_as_inactive(), test_a_tier_change_is_recorded_with_old_and_new_tier(), test_an_empty_or_collapsed_list_never_removes_anything(), test_new_removed_and_restored_roles_are_recorded() (+3 more)

### Community 17 - "jobs/models.py"
Cohesion: 0.16
Nodes (6): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), JobEvent, Base

### Community 18 - "green_list/service.py"
Cohesion: 0.17
Nodes (10): GreenListEvent, GreenListEventType, get_green_list(), get_green_list_changes(), GreenListChange, GreenListChangesResponse, GreenListResponse, GreenListRoleItem (+2 more)

### Community 19 - "TrendsPanel.tsx"
Cohesion: 0.11
Nodes (34): getLocations(), getSources(), getTrends(), ChartCard(), ChartCardProps, ChartShell(), ChartShellProps, ChartTable() (+26 more)

### Community 20 - "Project guidance"
Cohesion: 0.25
Nodes (7): Agent and model selection, Async and data, Errors and exceptions, graphify, Monorepo, Project guidance, Quality checks

### Community 21 - "useApi"
Cohesion: 0.16
Nodes (21): getCategories(), loadSources(), Settled, useApi(), App(), CategorySwitcher(), CategorySwitcherProps, DebouncedFieldProps (+13 more)

### Community 22 - "test_normalization.py"
Cohesion: 0.24
Nodes (5): test_classify_seniority_reads_level_words_from_the_title(), test_get_pay_period_preserves_current_salary_rules(), test_normalize_text_collapses_whitespace(), test_parse_salary_estimates_an_annual_range_or_nothing(), test_region_of_is_the_last_part_of_a_seek_location()

### Community 23 - "client.ts"
Cohesion: 0.12
Nodes (23): ApiError, CategoryItem, get(), getGreenList(), getGreenListChanges(), GreenListChange, GreenListChangesResponse, GreenListResponse (+15 more)

### Community 24 - "AppError"
Cohesion: 0.13
Nodes (11): AppError, ErrorCode, ErrorDefinition, fetch_search_page(), parse_search_page(), SearchPage, app_error_probe(), test_app_error_exposes_catalog_message_and_keeps_detail_for_logs() (+3 more)

### Community 26 - "Jobs.tsx"
Cohesion: 0.15
Nodes (23): getCategoryJobs(), getJobFacets(), JobFacets, JobSource, JobStatus, DEFAULT_PARAMS, hasActiveFilters(), JobParams (+15 more)

### Community 27 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 29 - "configure_logging"
Cohesion: 0.05
Nodes (37): job_scout_employmenthero_daily(), discover(), enabled_categories(), enrich(), reconcile(), sync(), job_scout_green_list_monthly(), sync_green_list() (+29 more)

### Community 30 - "test_job_events.py"
Cohesion: 0.49
Nodes (10): enriched(), events_for(), promote(), test_changed_fields_are_recorded_as_an_updated_event(), test_promoting_a_new_job_records_a_new_event(), test_promoting_an_inactive_job_records_reopened(), test_promoting_unchanged_data_again_records_nothing(), test_promotion_stores_the_parsed_annual_salary() (+2 more)

### Community 31 - "test_employmenthero.py"
Cohesion: 0.16
Nodes (16): eh_site(), fetch_job(), job_page(), list_page(), test_a_seek_draft_with_the_same_id_does_not_count_as_seen_for_employment_hero(), test_build_description_turns_html_into_readable_text(), test_discovery_fails_closed_when_a_job_page_cannot_be_read(), test_discovery_fails_closed_when_the_first_page_has_no_jobs() (+8 more)

### Community 32 - "normalization.py"
Cohesion: 0.19
Nodes (3): upgrade(), classify_seniority(), region_of()

### Community 33 - "jobColumns.tsx"
Cohesion: 0.22
Nodes (12): getJob(), JobListItem, sourceLabel(), column(), Header(), jobColumns, PositionCell(), StatusChip() (+4 more)

### Community 35 - "phases.py"
Cohesion: 0.21
Nodes (10): enrich(), main(), run_once(), _category_id(), discover_phase(), enrich_phase(), reconcile_phase(), run_all_phases() (+2 more)

### Community 36 - "green_db"
Cohesion: 0.36
Nodes (3): green_api(), override_session(), green_db()

### Community 39 - "test_job_boards.py"
Cohesion: 0.12
Nodes (8): fake_pages(), pages_gen(), no_real_clients(), _NoClient, test_discovery_fails_closed_when_a_page_cannot_be_read(), test_discovery_fails_closed_when_the_first_page_has_no_jobs(), test_discovery_saves_drafts_for_every_listed_job(), test_indeed_parse_search_without_job_search_is_a_source_error()

### Community 40 - "parse_record"
Cohesion: 0.24
Nodes (9): html_to_text(), parse_record(), inz_record(), test_a_record_without_a_tier_is_rejected_instead_of_guessed(), test_a_record_without_an_id_is_rejected(), test_html_to_text_keeps_lists_and_drops_markup_and_scripts(), test_parse_record_reads_the_role_fields(), test_parse_record_reads_tier_two_and_a_real_note() (+1 more)

### Community 41 - "discovery.py"
Cohesion: 0.21
Nodes (10): discover(), discover_employmenthero(), discover_job_board(), discoverer(), DiscoverySummary, reconcile_active_jobs(), normalize_text(), get_enabled_category() (+2 more)

### Community 42 - "test_api.py"
Cohesion: 0.47
Nodes (6): roles(), test_a_role_that_changed_tier_says_so_and_a_removed_one_is_hidden(), test_an_empty_table_returns_zeros(), test_changes_list_newest_first_with_what_changed(), test_changes_validate_the_period(), test_roles_come_with_tier_counts_sorted_by_title()

### Community 43 - "employmenthero.py"
Cohesion: 0.21
Nodes (10): build_description(), client(), fetch_job_page(), fetch_list_page(), _get(), job_url(), normalize_listing(), parse_job_posting() (+2 more)

### Community 44 - "test_errors.py"
Cohesion: 0.43
Nodes (4): test_application_error_uses_catalog_status_and_message(), test_http_not_found_uses_central_error_response(), test_request_validation_uses_central_error_response(), test_unexpected_error_is_logged_and_redacted()

### Community 45 - "errors.py"
Cohesion: 0.15
Nodes (9): fetch_green_list(), _Meta, _Page, _Response, main(), RoleRecord, _content(), sync_green_list() (+1 more)

### Community 46 - "persistence.py"
Cohesion: 0.24
Nodes (6): upgrade(), JobEventType, parse_salary(), draft_key(), _json_value(), _promotion_events()

### Community 47 - "categories/service.py"
Cohesion: 0.23
Nodes (4): get_categories(), CategoryItem, list_categories(), get_session()

### Community 49 - "glassdoor.py"
Cohesion: 0.16
Nodes (10): client(), request(), build_description(), client(), _descriptions(), _graph(), normalize_listing(), pages() (+2 more)

### Community 50 - "inz_record"
Cohesion: 0.22
Nodes (8): fetch(), response(), test_a_non_json_answer_is_refused(), test_an_incomplete_or_odd_response_is_refused(), test_fetch_sends_the_green_list_query_and_parses_every_role(), handler(), test_transient_server_errors_are_retried_then_given_up(), flaky()

### Community 53 - "indeed.py"
Cohesion: 0.17
Nodes (11): build_description(), build_query(), client(), normalize_listing(), pages(), parse_search(), _salary_label(), build_description() (+3 more)

### Community 54 - "devDependencies"
Cohesion: 0.17
Nodes (12): devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, globals, openapi-typescript, @types/react, @types/react-dom (+4 more)

### Community 55 - "re"
Cohesion: 0.21
Nodes (6): downgrade(), slugify(), upgrade(), test_database_check_allows_exactly_the_declared_sources(), test_every_declared_source_can_be_scraped_and_enriched(), test_unknown_source_is_rejected_instead_of_silently_scraped()

### Community 56 - "test_phases.py"
Cohesion: 0.40
Nodes (4): test_database(), test_employment_hero_covers_only_categories_with_a_sector_id(), test_one_named_category_must_exist_and_be_enabled(), test_the_daily_run_covers_every_enabled_category()

### Community 57 - "dependencies"
Cohesion: 0.25
Nodes (8): dependencies, @emotion/react, @emotion/styled, @mui/material, @mui/x-data-grid, react, react-dom, react-router-dom

### Community 62 - "scripts"
Cohesion: 0.33
Nodes (6): scripts, build, dev, gen:api, lint, preview

### Community 63 - "eslint.config.js"
Cohesion: 0.40
Nodes (4): @eslint/js, eslint-plugin-react-hooks, globals, typescript-eslint

## Knowledge Gaps
- **8 isolated node(s):** `job-scout`, `@emotion/react`, `@emotion/styled`, `@types/react`, `@types/react-dom` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 360 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppError` connect `AppError` to `test_main.py`, `test_immigration_client.py`, `Category`, `test_seek_client.py`, `source_listing`, `apply_sync`, `configure_logging`, `test_employmenthero.py`, `phases.py`, `test_job_boards.py`, `parse_record`, `discovery.py`, `employmenthero.py`, `errors.py`, `categories/service.py`, `glassdoor.py`, `inz_record`, `indeed.py`, `test_phases.py`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `AppError` (e.g. with `app_error_handler()` and `register_exception_handlers()`) actually correct?**
  _`AppError` has 40 INFERRED edges - model-reasoned connections that need verification._
- **What connects `job-scout`, `@emotion/react`, `@emotion/styled` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10344827586206896 - nodes in this community are weakly interconnected._
- **Why does `ErrorCode` connect `AppError` to `test_main.py`, `test_immigration_client.py`, `Category`, `test_seek_client.py`, `source_listing`, `apply_sync`, `configure_logging`, `test_employmenthero.py`, `phases.py`, `parse_record`, `discovery.py`, `employmenthero.py`, `errors.py`, `persistence.py`, `categories/service.py`, `glassdoor.py`, `inz_record`, `indeed.py`, `test_phases.py`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `ErrorCode` (e.g. with `require_enabled_category()` and `error_response()`) actually correct?**
  _`ErrorCode` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_immigration_client.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._