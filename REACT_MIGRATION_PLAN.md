# React research workbench migration

## Objective and ownership

Preserve Python/FastAPI/LangGraph and the HTTP-only FinancialReports boundary.
Use React + TypeScript for the research workbench; financial calculations remain
in the existing backend services. The legacy UI remains available until the new
pages pass equivalent interaction checks.

Implementation started from `31913bc` on `feat/react-research-workbench`.
The supervising Codex owns architecture, integration and validation. Three
herdr Codex sessions using `gpt-5.6-luna` implement disjoint areas: backend API
contracts, React frontend, and legacy UI regression fixes. No external publish,
PR, merge or deployment is part of the current local implementation.

## Acceptance checklist

- [x] Preserve financial API payloads while adding typed OpenAPI responses.
- [x] State currency, money units, percentage/ratio semantics and absence states.
- [x] Remove inline financial/demo calculations from the four legacy analysis pages.
- [x] Nullable Snapshot results render and survive download/other interactions.
- [x] Research mode is selectable and full responses replay/export correctly.
- [x] React discovery and all analysis pages use the backend API exclusively.
- [x] Requests cannot overwrite a newer submitted query with an older result.
- [x] Browser history is explicitly local history, not model conversation memory.
- [x] Frontend types are generated from the backend contract and checked for drift.
- [x] Backend tests, types, format and frontend build/interaction tests pass.
- [x] Local frontend/backend startup and container definitions are documented.

All eleven items above were re-verified in a follow-up integration pass after the
three delegated `gpt-5.6-luna` sessions hit their usage limit mid-review. Two of
the three status reports were written *before* the supervising review's fix list
landed, so their "complete" claims were checked against the real backend contract
rather than trusted:

- `ui/pages/ews.py` still read `signals`/`name`; the API returns
  `triggered_signals`/`signal_name`/`current_value`/`threshold_value`. Its own
  regression-test fixture used the same wrong keys, so the test passed while the
  page silently showed zero signals. Fixed in both the page and the fixture, and
  the assertion now checks the rendered signal text, not just "no exception".
- `frontend/src/types.ts`'s `Snapshot` type (`identity`/flat `snapshot.net_revenue`)
  didn't match `FinancialSnapshotResponse`'s real nested shape
  (`identification`/`income_statement`/`margins`/`balance_sheet`/
  `financial_structure`/`returns`/`data_context`). Its own Vitest mock used the
  same wrong shape. Fixed, and the frontend's `Snapshot`/`AgentResponse` types
  are now derived from `frontend/src/api.generated.ts` (via `npm run
  generate:api`) instead of hand-written, closing this whole class of drift —
  confirmed by re-running typecheck, which caught one real `undefined` case from
  the switch.
- `frontend`'s `AnalysisPage` sent `trend`/`earnings_quality`/`ews` (all GET-only
  routes) as POST through a single `postAnalysis` helper. Split into
  `getAnalysis`/`postAnalysis` by route method, with a Vitest test asserting the
  EWS page fetch is not a POST.
- `ui/pages/snapshot.py`'s capital-structure pie chart passed nullable
  `debt_ratio`/`equity_ratio` straight to Plotly instead of the `or 0` fallback
  the margins chart already used; brought in line (not a crash — Plotly accepts
  `None` — but inconsistent with the "nullable values never crash/misrender"
  goal).

Backend's typed contracts (`app/models/api_models.py`,
`tests/test_api_contracts.py`, `scripts/export_openapi.py`) were, despite no
status file being left behind (the session was cut off before it could write
one), actually complete and passing.

Verified together: `pytest` 201 passed / 5 skipped, `mypy` clean, `black`
clean, `python -m evaluation` (isolated) still 100%/100%/100%, frontend
`typecheck`/`test`(4 passed)/`build` all clean.

## Subsequent production gate

Deployment audience determines identity, authorization, persistence and task
execution requirements. Do not describe browser history as durable server jobs,
client request cancellation as server cancellation, or citation presence as
claim correctness. Server-owned research jobs, per-user authorization, shared
cache/rate limits and evidence-based claim evaluation require their own tested
implementation before a production-readiness claim.

## Baseline evidence

191 pytest tests passed and 5 producer smoke tests skipped. Mypy passed its
33-file scope; Black rejected `app/core/utils.py` and `ui/pages/agent.py`.
AppTest reproduced missing model properties after submitting earnings quality,
ROIC/WACC and factor forms; Snapshot null revenue crashes and its nested download
button clears results. Four pages calculate locally while API/Agent services use
different inputs/methods. GitHub status could not be checked (403); the local
Docker daemon reported no running containers during assessment.
