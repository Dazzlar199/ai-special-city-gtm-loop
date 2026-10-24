# Prospect Discovery Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable, evidence-based prospect discovery pipeline that collects public brand candidates, removes duplicates and disqualified records, scores observable fit, and places only reviewable candidates in the local sales dashboard.

**Architecture:** A Python discovery service owns source queries, normalization, evidence gates, scoring, deduplication, and persisted results. The existing local HTTP server exposes read-only discovery results and a deliberate `POST /api/discover` trigger; the browser dashboard displays the queue and never sends outreach automatically. Source adapters are independent so public search or directory changes do not affect scoring and CRM state.

**Tech Stack:** Python 3 standard library, JSON persistence, Node test runner for browser model tests, Python unittest for discovery engine tests, existing HTML/CSS/ES modules.

**Spec:** `/Users/dazzlar/Desktop/coding/new_store/AI_Special_City_AX_Commerce_Growth_Strategy.md` section 5, amended by the approved two-stage public discovery/qualification design in this conversation.

## Global Constraints

- Public information only; no login bypass, CAPTCHA bypass, or private contact collection.
- A candidate needs a current official sales/activity source and a public business contact path before outreach eligibility.
- Public discovery score uses only observable evidence; operational pain, margin, delegation willingness, and urgency remain interview fields.
- Closed businesses, reseller-only stores, inactive records, and duplicates never enter the active review queue.
- Discovery never sends messages; final outreach remains a separate approved action.
- Every fact stores source URL and checked date; unknown values remain unknown.

## Review Focus

- Duplicate brands using different spelling or URLs must merge without losing evidence.
- A search result without an official brand/store page must remain unqualified.
- Missing public contact must block outreach even when fit score is high.
- Stale or stopped stores must be excluded instead of merely receiving a low score.
- Network failures or page-layout changes must preserve existing results and report the failing source.

---

### Task 1: Evidence schema, gates, and public fit score

**Files:**
- Create: `outbound-dashboard/discovery/scoring.py`
- Create: `outbound-dashboard/discovery/models.py`
- Test: `outbound-dashboard/discovery/tests/test_scoring.py`

**Interfaces:**
- Consumes: normalized candidate dictionaries from source adapters.
- Produces: `evaluate_candidate(candidate, today) -> evaluation` with hard-gate result, 0-100 public fit score, reasons, known facts, and unknowns.

- [x] Write failing tests for the seven score components, unknown evidence, stopped stores, missing contact, reseller-only records, and the 60-day activity boundary.
- [x] Run the tests and confirm failures are caused by missing discovery modules.
- [x] Implement the normalized candidate model and hard gates.
- [x] Implement the public score: own products 20, recent activity 15, channel gap 20, workload complexity 15, category expansion 15, contactability 10, evidence quality 5.
- [x] Run the scoring tests and confirm they pass.

### Task 2: Identity resolution and durable discovery store

**Files:**
- Create: `outbound-dashboard/discovery/dedupe.py`
- Create: `outbound-dashboard/discovery/store.py`
- Create: `outbound-dashboard/data/discovery-results.json`
- Test: `outbound-dashboard/discovery/tests/test_store.py`

**Interfaces:**
- Consumes: evaluated candidates.
- Produces: `merge_candidates(records) -> records` and atomic `DiscoveryStore` read/write operations.

- [ ] Add the remaining forced-write-failure test for atomic preservation; duplicate identities, evidence union, stable IDs, and malformed JSON are covered.
- [x] Run the tests and confirm expected failures.
- [x] Implement deterministic identity keys and evidence-preserving merge behavior.
- [x] Implement atomic JSON persistence with run metadata and source errors.
- [x] Run the store tests and confirm they pass.

### Task 3: Public source adapters and query registry

**Files:**
- Create: `outbound-dashboard/discovery/sources.py`
- Create: `outbound-dashboard/discovery/queries.json`
- Create: `outbound-dashboard/discovery/discover.py`
- Test: `outbound-dashboard/discovery/tests/test_sources.py`

**Interfaces:**
- Consumes: source definitions and public HTML/search responses.
- Produces: normalized candidate stubs with source type, official URL, evidence URL, excerpt, and checked date.

- [ ] Add dedicated captured-HTML fixtures for Wadiz, exhibition directories, and Fanfandaero; current fixtures cover Naver redirects and supported URL classification.
- [x] Run tests and confirm they fail because adapters are absent.
- [x] Implement polite public fetches with timeouts, bounded results, identifiable user agent, and no retry loops around blocks or CAPTCHAs.
- [x] Implement query templates by category and source, link extraction, source-type classification, and error reporting.
- [x] Run source tests against fixed HTML fixtures and confirm they pass.
- [x] Run a bounded live smoke test; record unsupported sources without failing the entire run.

### Task 4: Local API and dashboard discovery controls

**Files:**
- Modify: `outbound-dashboard/serve.py`
- Modify: `outbound-dashboard/index.html`
- Modify: `outbound-dashboard/styles.css`
- Modify: `outbound-dashboard/app.mjs`
- Modify: `outbound-dashboard/app-model.mjs`
- Test: `outbound-dashboard/discovery/tests/test_api.py`
- Test: `outbound-dashboard/tests/app-model.test.mjs`

**Interfaces:**
- Consumes: `DiscoveryStore` and `run_discovery(limit, categories)`.
- Produces: `GET /api/prospects`, `GET /api/discovery-status`, and confirmation-gated `POST /api/discover`.

- [ ] Add direct concurrent-run and network-failure API tests; successful reads, bounds, invalid input, confirmation, and zero-send behavior are covered.
- [x] Write failing browser-model tests for score ordering, excluded candidates, and source freshness display.
- [x] Implement API endpoints and bounded discovery execution without exposing credentials.
- [x] Add a restrained `후보 찾기` control, source/status summary, score reasons, and refresh behavior to the dashboard.
- [x] Keep the existing five reviewed candidates available while migrating new discoveries to the durable store.
- [x] Run Python and Node suites and confirm they pass.

### Task 5: Live source run, evidence audit, and acceptance verification

**Files:**
- Modify: `outbound-dashboard/data/discovery-results.json`
- Create: `outbound-dashboard/discovery/tests/fixtures/` as needed for observed public formats.

**Interfaces:**
- Consumes: complete discovery pipeline and current public sources.
- Produces: a deduplicated review queue with run time, source coverage, rejected-count reasons, and zero outbound sends.

- [x] Run one bounded discovery across SmartStore/Instagram search, Wadiz/Tumblbug, selected exhibitions, and Fanfandaero.
- [ ] Manually inspect every candidate admitted to the review queue against its evidence URL.
- [x] Confirm stopped, duplicate, contactless, and reseller-only records are rejected or held outside the outreach-eligible queue.
- [x] Verify the dashboard at desktop and narrow widths, all automated tests, browser console, and send lock.
- [x] Record live-source coverage in discovery status without representing zero-result sources as qualified leads.
