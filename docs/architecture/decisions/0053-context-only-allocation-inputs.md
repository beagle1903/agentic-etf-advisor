# ADR 0053: Disclose context-only allocation inputs

- Status: Accepted for Issue154 after separate architect advice and coordinator approval.
- Date: 2026-11-17.
- Authority: [approved agreement](https://github.com/beagle1903/agentic-etf-advisor/issues/154#issuecomment-6945962777).

Risk tolerance selects the existing growth/defensive policy bands and objective
selects the target within them. Horizon and maximum tolerable drawdown are required,
validated human-review context; they do not change the target split. The calculation
does not enforce a drawdown limit or assess whether the allocation fits the horizon.

Disclose this consistently in initial/revision forms, review allocation, displayed
Policy notes, explanation display and CLI output. Presentation adds the disclosure
without editing saved policy notes, explanation text/limitations, artifacts, receipts,
reference indexes, graph state, revision routing, selectors or financial arithmetic.
An additional static provider system instruction explains the same boundary for
future calls. Existing successful receipts reuse their saved result. Explicit new
attempts/retries use the current adapter instruction, which is not part of the
operation digest. This does not promise exact historical prompt replay or perfect
semantic entailment enforcement. Historical explanations remain byte-preserved;
the current notice appears before them, including on offline restore.

This is disclosure, not a suitability engine, forecast or risk-protection mechanism.
No source/provider call, store migration, trade or external financial write is
introduced. See [iteration054](../../iterations/054-issue154-context-only-inputs.md)
for the frozen acceptance and verification evidence.
