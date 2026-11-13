# Graph Report - jobs  (2026-11-13)

## Corpus Check
- 144 files · ~40,858 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 8, .example 1, .ini 1)

## Summary
- 1188 nodes · 3268 edges · 50 communities (38 shown, 12 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 426 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bb138862`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_main.py
- test_immigration_client.py
- Category
- enrichment.py
- test_migrations.py
- Category
- ColumnFilterForm.tsx
- package.json
- test_seek_client.py
- compilerOptions
- source_listing
- job-scout
- discovery.py
- apply_sync
- TrendsPanel.tsx
- Project guidance
- useApi
- test_normalization.py
- client.ts
- Jobs.tsx
- schema.d.ts
- job_scout/main.py
- test_job_events.py
- test_employmenthero.py
- sqlalchemy
- Job Scout
- test_enrichment.py
- AppError
- test_job_boards.py
- JobDraft
- employmenthero.py
- discovery.py
- parse_record
- vercel.json
- glassdoor.py
- errors.py
- indeed.py
- test_exhausted_accreditation_retries_are_recorded_as_failure
- errors.py
- test_seek_client_description.py
- scrape_one
- test_empty_complete_scrape_marks_jobs_inactive_without_deleting_them
- test_errors.py

## God Nodes (most connected - your core abstractions)
1. `AppError` - 100 edges
2. `ErrorCode` - 74 edges
3. `Job` - 66 edges
4. `Category` - 61 edges
5. `source_listing()` - 48 edges
6. `JobDraft` - 33 edges
7. `configure_logging()` - 26 edges
8. `apply_sync()` - 23 edges
9. `@mui/material` - 22 edges
10. `run()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `enabled_categories()` --calls--> `configure_logging()`  [INFERRED]
  airflow/dags/employmenthero_sync.py → backend/src/job_scout/core/logging.py
- `enabled_categories()` --calls--> `enabled_category_slugs()`  [INFERRED]
  airflow/dags/employmenthero_sync.py → backend/src/job_scout/scraper/phases.py
- `discover()` --calls--> `configure_logging()`  [INFERRED]
  airflow/dags/employmenthero_sync.py → backend/src/job_scout/core/logging.py
- `discover()` --calls--> `discover_phase()`  [INFERRED]
  airflow/dags/employmenthero_sync.py → backend/src/job_scout/scraper/phases.py
- `reconcile()` --calls--> `configure_logging()`  [INFERRED]
  airflow/dags/employmenthero_sync.py → backend/src/job_scout/core/logging.py

## Import Cycles
- None detected.

## Communities (50 total, 12 thin omitted)

### Community 0 - "test_main.py"
Cohesion: 0.10
Nodes (15): _Session, test_command_accepts_the_job_board_sources(), test_command_configures_shared_logging(), complete(), test_discover_phase_prints_scan_timestamp(), test_enrich_phase_returns_failure_when_drafts_remain_failed(), test_full_run_exits_nonzero_when_listings_failed(), run_all() (+7 more)

### Community 1 - "test_immigration_client.py"
Cohesion: 0.14
Nodes (12): check_accreditation(), extract_immigration_fields(), is_accredited(), StubPage, test_accreditation_rule_preserves_current_non_no_results_behavior(), test_check_accreditation_raises_after_three_failures(), test_check_accreditation_reloads_the_page_when_a_lookup_fails(), test_check_accreditation_retries_then_returns_result() (+4 more)

### Community 2 - "Category"
Cohesion: 0.08
Nodes (34): Category, Job, api_context(), test_categories_returns_enabled_category_with_active_job_count(), _list(), _positions(), test_arrangement_and_work_type_filters_match_any_selected_value(), test_bad_sort_and_filter_values_are_validation_errors() (+26 more)

### Community 3 - "enrichment.py"
Cohesion: 0.23
Nodes (5): enrich(), _full_seek_description(), process_listing(), build_description(), normalize_text()

### Community 4 - "test_migrations.py"
Cohesion: 0.10
Nodes (16): async_test_database_url(), postgres_url(), sync_test_database_url(), connection(), test_every_seek_classification_is_seeded_and_only_ict_is_enabled(), test_green_list_tables_exist_and_events_follow_their_role(), test_job_event_table_records_job_history_and_follows_its_job(), test_jobs_carry_a_source_and_ids_are_unique_per_source() (+8 more)

### Community 5 - "Category"
Cohesion: 0.05
Nodes (40): get_categories(), CategoryItem, list_categories(), require_enabled_category(), get_session(), build_location_breakdown(), get_location_breakdown(), get_category_job_facets() (+32 more)

### Community 6 - "ColumnFilterForm.tsx"
Cohesion: 0.13
Nodes (27): sourceLabel(), clearAllFilters(), clearFilter(), describeFilter(), FIELD_LABELS, FILTER_FIELDS, FilterField, isFilterActive() (+19 more)

### Community 7 - "package.json"
Cohesion: 0.04
Nodes (46): dependencies, @emotion/react, @emotion/styled, @mui/material, @mui/x-data-grid, react, react-dom, react-router-dom (+38 more)

### Community 8 - "test_seek_client.py"
Cohesion: 0.18
Nodes (10): client(), _fetch_with_responses(), fake_sleep(), test_fetch_search_page_does_not_retry_client_errors(), test_fetch_search_page_follows_seek_market_redirect(), test_fetch_search_page_gives_up_after_three_attempts(), test_fetch_search_page_rejects_non_object_payload_with_central_error(), test_fetch_search_page_retries_transient_server_errors_with_backoff() (+2 more)

### Community 10 - "compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+8 more)

### Community 11 - "source_listing"
Cohesion: 0.16
Nodes (18): source_listing(), test_changed_payload_resets_attempts_and_makes_a_draft_pending_again(), fetch_page(), test_discovery_logs_which_response_check_failed(), test_discovery_persists_pending_drafts_without_enrichment(), fetch_page(), test_drafts_are_saved_once_per_seek_page(), fetch_page() (+10 more)

### Community 17 - "discovery.py"
Cohesion: 0.08
Nodes (32): job_scout_employmenthero_daily(), discover(), enabled_categories(), enrich(), reconcile(), sync(), job_scout_green_list_monthly(), sync_green_list() (+24 more)

### Community 18 - "apply_sync"
Cohesion: 0.09
Nodes (26): GreenListEvent, GreenListEventType, GreenListRole, get_green_list(), get_green_list_changes(), GreenListChange, GreenListChangesResponse, GreenListResponse (+18 more)

### Community 19 - "TrendsPanel.tsx"
Cohesion: 0.12
Nodes (31): ChartCard(), ChartCardProps, ChartShell(), ChartShellProps, ChartTable(), ChartTableProps, BarItem, HorizontalBarChart() (+23 more)

### Community 20 - "Project guidance"
Cohesion: 0.25
Nodes (7): Agent and model selection, Async and data, Errors and exceptions, graphify, Monorepo, Project guidance, Quality checks

### Community 21 - "useApi"
Cohesion: 0.14
Nodes (24): getCategories(), getJob(), loadSources(), Settled, useApi(), App(), CategorySwitcher(), CategorySwitcherProps (+16 more)

### Community 22 - "test_normalization.py"
Cohesion: 0.24
Nodes (5): test_classify_seniority_reads_level_words_from_the_title(), test_get_pay_period_preserves_current_salary_rules(), test_normalize_text_collapses_whitespace(), test_parse_salary_estimates_an_annual_range_or_nothing(), test_region_of_is_the_last_part_of_a_seek_location()

### Community 23 - "client.ts"
Cohesion: 0.10
Nodes (27): ApiError, CategoryItem, get(), getGreenList(), getGreenListChanges(), getLocations(), getSources(), getTrends() (+19 more)

### Community 26 - "Jobs.tsx"
Cohesion: 0.11
Nodes (29): getCategoryJobs(), getJobFacets(), JobFacets, JobSource, JobStatus, SOURCE_LABELS, hasActiveFilters(), JobParams (+21 more)

### Community 27 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 29 - "job_scout/main.py"
Cohesion: 0.11
Nodes (14): app_error_handler(), error_response(), http_error_handler(), register_exception_handlers(), unexpected_error_handler(), validation_error_handler(), health(), lifespan() (+6 more)

### Community 30 - "test_job_events.py"
Cohesion: 0.49
Nodes (10): enriched(), events_for(), promote(), test_changed_fields_are_recorded_as_an_updated_event(), test_promoting_a_new_job_records_a_new_event(), test_promoting_an_inactive_job_records_reopened(), test_promoting_unchanged_data_again_records_nothing(), test_promotion_stores_the_parsed_annual_salary() (+2 more)

### Community 31 - "test_employmenthero.py"
Cohesion: 0.16
Nodes (17): eh_site(), fetch_job(), job_page(), list_page(), test_a_seek_draft_with_the_same_id_does_not_count_as_seen_for_employment_hero(), test_build_description_turns_html_into_readable_text(), test_discovery_fails_closed_when_a_job_page_cannot_be_read(), test_discovery_fails_closed_when_the_first_page_has_no_jobs() (+9 more)

### Community 33 - "sqlalchemy"
Cohesion: 0.06
Nodes (26): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), upgrade(), upgrade(), upgrade(), upgrade() (+18 more)

### Community 35 - "test_enrichment.py"
Cohesion: 0.19
Nodes (17): _seed_pending(), test_accredited_job_description_comes_from_the_search_result(), test_accredited_listing_without_any_description_is_recorded_as_failed(), test_accredited_seek_job_gets_the_full_description(), test_app_error_keeps_its_own_code_when_recorded_on_the_draft(), test_drafts_that_exhausted_their_attempts_are_not_retried(), test_enrichment_retries_failed_drafts_but_skips_completed_drafts(), test_failed_enrichment_increments_attempts() (+9 more)

### Community 38 - "AppError"
Cohesion: 0.13
Nodes (11): AppError, ErrorCode, fetch_search_page(), parse_search_page(), SearchPage, app_error_probe(), test_app_error_exposes_catalog_message_and_keeps_detail_for_logs(), test_error_detail_is_never_sent_to_clients() (+3 more)

### Community 39 - "test_job_boards.py"
Cohesion: 0.12
Nodes (8): fake_pages(), pages_gen(), no_real_clients(), _NoClient, test_discovery_fails_closed_when_a_page_cannot_be_read(), test_discovery_fails_closed_when_the_first_page_has_no_jobs(), test_discovery_saves_drafts_for_every_listed_job(), test_indeed_parse_search_without_job_search_is_a_source_error()

### Community 41 - "JobDraft"
Cohesion: 0.16
Nodes (7): JobDraft, _status(), test_noisy_seek_fields_do_not_reset_a_completed_draft(), test_run_does_not_count_exhausted_drafts_as_new_failures(), fetch_page(), test_scrape_commits_draft_before_enrichment_and_upserts_clean_job(), fetch_page()

### Community 43 - "employmenthero.py"
Cohesion: 0.15
Nodes (14): build_description(), fetch_job_page(), fetch_list_page(), _get(), job_url(), normalize_listing(), parse_job_posting(), parse_job_slugs() (+6 more)

### Community 44 - "discovery.py"
Cohesion: 0.12
Nodes (17): JobEvent, JobEventType, discover(), discover_employmenthero(), discover_job_board(), discoverer(), DiscoverySummary, reconcile_active_jobs() (+9 more)

### Community 45 - "parse_record"
Cohesion: 0.08
Nodes (25): html_to_text(), parse_record(), _raw(), _TextExtractor, inz_record(), roles(), test_a_role_that_changed_tier_says_so_and_a_removed_one_is_hidden(), test_an_empty_table_returns_zeros() (+17 more)

### Community 49 - "glassdoor.py"
Cohesion: 0.32
Nodes (7): build_description(), client(), _descriptions(), _graph(), pages(), parse_listing(), _search_variables()

### Community 52 - "errors.py"
Cohesion: 0.12
Nodes (7): Settings, main(), backfill(), main(), client(), request(), fetch_description()

### Community 55 - "indeed.py"
Cohesion: 0.27
Nodes (7): build_description(), build_query(), client(), normalize_listing(), pages(), parse_search(), _salary_label()

### Community 59 - "test_exhausted_accreditation_retries_are_recorded_as_failure"
Cohesion: 0.15
Nodes (9): make_job(), test_bad_immigration_payload_is_recorded_and_does_not_overwrite_job(), fetch_page(), test_exhausted_accreditation_retries_are_recorded_as_failure(), accreditation(), fetch_page(), test_non_accredited_result_preserves_existing_clean_job(), fetch_page() (+1 more)

### Community 60 - "errors.py"
Cohesion: 0.19
Nodes (7): ErrorDefinition, fetch_green_list(), _Meta, _Page, _Response, RoleRecord, _content()

### Community 63 - "test_seek_client_description.py"
Cohesion: 0.33
Nodes (4): _Http, _Response, test_fetch_description_is_none_when_seek_has_no_job(), test_fetch_description_turns_html_into_text()

### Community 67 - "test_errors.py"
Cohesion: 0.43
Nodes (4): test_application_error_uses_catalog_status_and_message(), test_http_not_found_uses_central_error_response(), test_request_validation_uses_central_error_response(), test_unexpected_error_is_logged_and_redacted()

## Knowledge Gaps
- **8 isolated node(s):** `job-scout`, `@emotion/react`, `@emotion/styled`, `@types/react`, `@types/react-dom` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 357 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppError` connect `AppError` to `test_main.py`, `test_immigration_client.py`, `enrichment.py`, `Category`, `test_seek_client.py`, `source_listing`, `discovery.py`, `apply_sync`, `job_scout/main.py`, `test_employmenthero.py`, `sqlalchemy`, `test_enrichment.py`, `test_job_boards.py`, `employmenthero.py`, `discovery.py`, `parse_record`, `glassdoor.py`, `errors.py`, `indeed.py`, `test_exhausted_accreditation_retries_are_recorded_as_failure`, `errors.py`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `AppError` (e.g. with `app_error_handler()` and `register_exception_handlers()`) actually correct?**
  _`AppError` has 44 INFERRED edges - model-reasoned connections that need verification._
- **What connects `job-scout`, `@emotion/react`, `@emotion/styled` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1032258064516129 - nodes in this community are weakly interconnected._
- **Why does `ErrorCode` connect `AppError` to `test_main.py`, `test_immigration_client.py`, `enrichment.py`, `Category`, `test_seek_client.py`, `source_listing`, `discovery.py`, `apply_sync`, `job_scout/main.py`, `test_employmenthero.py`, `sqlalchemy`, `test_enrichment.py`, `employmenthero.py`, `discovery.py`, `parse_record`, `glassdoor.py`, `errors.py`, `indeed.py`, `test_exhausted_accreditation_retries_are_recorded_as_failure`, `errors.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 54 inferred relationships involving `ErrorCode` (e.g. with `require_enabled_category()` and `error_response()`) actually correct?**
  _`ErrorCode` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_immigration_client.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13852813852813853 - nodes in this community are weakly interconnected._