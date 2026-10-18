# Iteration 026: Issue 112 explanation diagnostics

Issue [#112](https://github.com/beagle1903/agentic-etf-advisor/issues/112) uses the
ordinary `DESIGN_READY` capsule `issue-112-explanation-diagnostics`, generation 1,
digest `4bee9e5bef792b501a1b255efbd05782e28268bf041c703ba0ca00b945914b3e`.
The approved scope is the existing explanation provider boundary and its diagnostic and
generation guidance. Grounding, numeric support, safety, graph state, receipts, and review
semantics remain authoritative and unchanged.

The plain-text Cloud parser now parses one complete top-level JSON object before schema
validation. It accepts one object in surrounding prose or a Markdown fence, rejects
malformed leading JSON and multiple objects as ambiguous, and preserves the original
validation exception when the one complete explanation object fails its section rule.
Local JSON and Pydantic validation
failures receive the sanitized `invalid_response` diagnostic. A genuine HTTP 401/403
remains `authentication`; field errors such as `extra_forbidden` do not imply that class.
The [A112-1 coordinator decision](../workflow/issue-112-arbitration.md) fixed diagnostic
precedence: explicit HTTP status first, typed local parsing/schema errors next, then
provider text signals. Focused fixtures cover 401/403/429/503 wrappers, a provider
capability ValueError, and typed errors containing misleading provider-like phrases.

The generation instructions and plain-text request schema now state the existing summary,
policy-point, and evidence-point basis rules. Numeric wording directs the model to cite
the exact references that contain each claimed number. Deterministic validation remains
the final authority for all provider methods.

Synthetic fixtures confirmed that a policy number present in an exact cited field passes
and that the same number with an unrelated citation fails as
`unsupported_numeric_claim`. The historical rejected model text and references were not
retained. Its specific cause cannot be inferred from these fixtures; it remains
unconfirmed. No live provider call or saved-review mutation was made for this repair.

Focused provider and workflow tests cover wrong-summary validation preservation,
ambiguous multi-object output, nested `extra_forbidden`, HTTP authentication,
request-schema guidance, exact numeric citation, and the fake-provider graph boundary:
valid output reaches human review, while invalid output blocks before review with a
redacted diagnostic. This does not guarantee that a future model response will pass the
existing safety and grounding checks.
