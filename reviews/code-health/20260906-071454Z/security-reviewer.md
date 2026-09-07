# Security reviewer — 20260906-071454Z

## Scope and result

Audit-only inspection of checked-out commit `c25865f` (PR #45 merge), including the changes from `a876384..HEAD`. One confirmed **P2** finding; no confirmed P0 or P1 security findings. No application, test, dependency, configuration, or project-documentation changes were made. Only this report was written by this reviewer.

Read `AGENTS.md`, `wishlist.md`, product vision, current system architecture, accepted ADRs 0004, 0006, 0015 and 0016, and active Iteration 017 in the prescribed order. Scope was interpreted against the implemented #40 slice: #41 lifecycle and #42 dashboard work remain planned, not regressions.

Root owns the canonical starting-worktree inventory and complete frozen baseline results in SUMMARY.md. Root reported all required baseline gates passed: format (110 files), Ruff, mypy (44 source files), pytest (360 passed), retrieval evaluation (5 cases), explanation evaluation (8/8), packaging, and Compose validation. Targeted reproductions below used the successfully frozen external audit environment at `C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-venv/Scripts/python.exe`, with `PYTHONDONTWRITEBYTECODE=1` and `-B`. They made no network, model, market-data, database, or brokerage calls.

## SEC-01 — P2: Ordinary explicit trade instructions and recommendations pass the safety gate

- **Confidence:** High; reproduced through both the production bundle validator and production explanation node.
- **Affected lines:** `src/etf_advisor/explanation/models.py:50-70` (imperative, recommendation and forecast patterns), `src/etf_advisor/explanation/models.py:500-505` (normalization and matching), and `src/etf_advisor/graph/nodes.py:280-283` (accepted output becomes ready for human review).
- **Evidence:** The imperative pattern only recognizes the trading verb at the beginning of a sentence; a normal politeness prefix such as “Please” evades it. Recommendation matching recognizes selected active subjects and verbs but misses passive recommendations. Forecast matching recognizes only selected future constructions. In a known-valid packaged response, changing the first SPY evidence statement produced:

```text
ACCEPT: SPY is recommended for you. | ready
ACCEPT: Please buy SPY. | ready
ACCEPT: SPY shall outperform. | ready
REJECT: Buy SPY. | ExplanationContractError
```

The complete production `draft_explanation` node returned `awaiting_human_review`, the unchanged text `Please buy SPY.`, and an empty explanation error list. The original valid reference and matching SPY subject were preserved. This is a direct safety-boundary failure for explicit prohibited language, not an inference that general semantic entailment is solved or required.

- **Impact:** An optional model response, including one influenced by the untrusted source text, can present an explicit trade instruction, personalized recommendation, or forecast as a validated grounded explanation. Human review still exists and no trade is executed, which limits severity; nevertheless, the accepted educational/no-recommendation contract is violated before that review. Citation correctness and fixed limitations do not reject the instruction.
- **Minimal reproduction:** From the repository root, run the following using the frozen audit Python executable (PowerShell here-string piped to `python -B -` works without creating files):

```python
from etf_advisor.evaluation.explanation_offline import load_explanation_evaluation_dataset
from etf_advisor.explanation.models import validate_and_bundle_explanation
from etf_advisor.graph.nodes import draft_explanation

ds = load_explanation_evaluation_dataset()
base = next(c.result for c in ds.cases
            if c.result is not None and c.expected_decision == "accept")
for text in ("SPY is recommended for you.", "Please buy SPY.",
             "SPY shall outperform.", "Buy SPY."):
    result = base.model_copy(deep=True)
    result.explanation.evidence_points[0].text = text
    try:
        print(text, validate_and_bundle_explanation(ds.request, result).status)
    except ValueError as exc:
        print(text, type(exc).__name__)

result = base.model_copy(deep=True)
result.explanation.evidence_points[0].text = "Please buy SPY."
class FakeProvider:
    def generate(self, request):
        return result
state = {key: getattr(ds.request, key).model_dump(mode="json") for key in
         ("profile", "draft_policy", "candidate_evidence", "candidate_screening",
          "portfolio_construction")}
output = draft_explanation(state, generator=FakeProvider())
print(output["status"], output["explanation_errors"])
print(output["draft_explanation"]["explanation"]["evidence_points"][0]["text"])
```

### Remediation agent prompt

> Harden the deterministic explanation financial-language boundary in `src/etf_advisor/explanation/models.py` for ordinary explicit instructions, passive recommendations, and future-outperformance assertions. Reproduce `Please buy SPY.`, `SPY is recommended for you.`, and `SPY shall outperform.` using an otherwise valid explanation fixture; ensure each fails with `prohibited_claim` in the production validator, graph node, and restored-review path. Scope changes to explanation safety and focused regression/evaluation coverage; retain deterministic financial arithmetic, source/reference/subject validation, provider interfaces, sanitized errors, and human review. Do not add provider calls or claim comprehensive semantic entailment. Add nearby benign educational and negated-language examples to constrain false positives. Acceptance: all three reproductions fail closed with no review-ready draft or rejected raw text in error diagnostics, existing valid explanations remain accepted, and the explanation offline evaluation passes. Verify with `uv run pytest tests/test_explanation.py tests/test_explanation_evaluation.py tests/test_dashboard.py`, `uv run etf-advisor evaluate-explanations`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy`, and `uv run pytest`; complete repository-required packaging/Compose gates before delivery.

## Checks performed and security controls observed

- **Secrets and deployment boundary:** Inspected `config.py`, `checkpoint.py`, Compose, provider construction, CLI output and dashboard rendering. Secret settings use Pydantic `SecretStr`; Compose database ports bind to loopback. Public default passwords are explicitly development defaults, not discovered production credentials. A tracked-file, filename-only scan for PEM/OpenSSH private-key headers and common OpenAI/OpenRouter/AWS credential shapes returned no matches; tracked secret-like filename inventory contained only `.env.example`. Ignored `.env` values were not printed or collected. This is a limited pattern scan, not proof no secret exists in all Git history.
- **Source URLs and file paths:** Evidence and research provenance require HTTP(S) URLs with a netloc (`rag/evidence.py:521-526`, `research/models.py:64-72`). URLs are citation links, not arbitrary server-side fetch targets in the inspected paths. The allowlist does not establish publisher trust or public-address provenance. Snapshot default filenames sanitize version input and add a digest; publication uses exclusive hard-link creation and checks existing content rather than overwriting it (`research/snapshot_io.py`). No confirmed source-URL SSRF or path-traversal finding was identified.
- **Retrieved/model text:** Provider inputs separate a system policy from JSON source data, explicitly label source content untrusted, bound source excerpts, restrict selected-position sources, and publish exact request-scoped reference allowlists (`explanation/provider.py`). Pydantic forbids additional generated keys. Grounding checks validate basis, references, matching subjects and numeric-token support. The dashboard renders explanation/source body with `st.text`, rather than enabling raw HTML (`dashboard_app.py:310`, `:487`). These controls do not fix SEC-01 or prove semantic truth.
- **Neo4j parameterization:** Inspected query constants and call sites in `rag/neo4j_store.py`; source, symbol, snapshot, ID, and relationship values enter parameter dictionaries. `_execute` uses `parameters_` rather than interpolating these values into Cypher (`:395-405`). SDK failures become generic service-health messages (`:407-410`). No confirmed query-injection finding.
- **Review capability:** Durable restore normalizes a version-4 UUID and fetches only the named thread (`dashboard.py:274-312`); no saved-thread listing was introduced. The CLI suppresses the retained ledger from its state output. The local token is explicitly a capability, not authentication. Database administrators are outside the tamper-evidence threat boundary.
- **PR #45 replay and checkpoint changes:** Read `domain/revision.py`, `graph/revision.py`, relevant `graph/workflow.py` and `nodes.py`, with receipt/tamper/restore tests. The state seal is canonical JSON SHA-256; semantic validation additionally checks revision/thread/attempt identity, manifests, artifact digests and references. Separate prepare/execute steps and one-use runtime permits protect ambiguous replay; synchronous durability is enforced at guarded nodes. Succeeded receipt reuse revalidates outputs, and explicit retries require the last operation ID. Review recomputes policy, screening, construction, and explanation validation. Inspected tests include cross-thread restore, malformed receipts, altered outputs, checkpoint commit failure, asynchronous durability rejection, and safety revalidation. No additional confirmed security defect in these mechanisms was established.
- **Provider failures:** Inspected broad ordinary-exception capture, stable diagnostic categorization, generic logged fields, and fixed error messages in the LangChain adapter. OpenRouter retry count is explicitly zero. No raw model response is deliberately rendered on validation failure. Replacement adapters remain responsible for the sanitized error interface; malformed/malicious custom adapters and SDK-internal trace exports were not dynamically audited.
- **Unsafe financial writes:** Repository source/interface inspection found no implemented broker, order-execution, or automatic external financial-write path. Deterministic allocations and review decisions remain separate from trade execution.

## Planned work, hypotheses and limitations

- **Planned, not a finding:** Checkpoint retention, 30-day expiry, explicit prune/whole-thread deletion and their atomicity remain #41; typed interactive revision/retry/lifecycle UI remains #42. Current absence was not reported as a regression. Authentication, per-user authorization, concurrent editing and production deployment are expressly outside the current local prototype scope.
- **Unresolved safety limits:** The validator checks reference structure and numeric-token membership, not general semantic entailment, unit binding, every language, adversarial paraphrase, or source truth. SEC-01 gives concrete ordinary-language failures within the existing prohibition contract. No live model red-team campaign was performed.
- **Dependency risk:** Direct declarations and integration boundaries were reviewed; package advisory/outdated assessment belongs to the independent dependency reviewer. No CVE claims or clean-dependency assurance are made here.
- **Not evaluated:** Actual PostgreSQL/Neo4j/Chroma server configuration, extension/plugin security, database network ACLs, at-rest encryption, live SDK logging/tracing, browser referrers or access logs, provider endpoint TLS behavior, Git-history secret scanning, external penetration/load tests, and lifecycle behavior that has not yet been implemented.
- **Verification:** Two successful offline inline-Python commands reproduced SEC-01 with frozen dependencies and no project writes. Baseline gates were intentionally not duplicated because root executed them. Findings do not depend on a failing baseline. Audit report completion must not be interpreted as a passing code-health baseline; see SUMMARY.md for every gate result and final workspace verification.

