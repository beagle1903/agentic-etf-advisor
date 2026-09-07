# Coordinator targeted verification

Required baseline gates all passed once. No unchanged gate was repeated. Specialty reports contain their own executed offline reproductions. This additional probe strengthens ARCH-01 by testing optional-artifact presence, independently of the policy amount substitution.

## ARCH-01: Full review can be reduced to policy-only presentation

Executed with frozen external Python, bytecode disabled, using only in-memory test fixtures; exit 0. No project files or external services were used by the probe.

```python
import sys
from copy import deepcopy
from types import SimpleNamespace
sys.path.insert(0, "tests")
from test_revision import start
from etf_advisor.dashboard import review_payload
from etf_advisor.graph.revision import validate_revision_state
_, _, state, _, _ = start()
validate_revision_state(state)
payload = deepcopy(state["__interrupt__"][0].value)
for key in ("candidate_evidence", "candidate_screening",
            "portfolio_construction", "draft_explanation"):
    payload.pop(key, None)
state["__interrupt__"] = (SimpleNamespace(value=payload),)
result = review_payload(state)
print("valid_full_checkpoint=", bool(state["portfolio_construction"]))
print("stripped_full_review_accepted=", "portfolio_construction" not in result)
```

Observed:

```text
valid_full_checkpoint= True
stripped_full_review_accepted= True
```

The revision seal still validates the authoritative full checkpoint. The interrupt retains the correct revision ID and policy, but the conditional validation at `src/etf_advisor/dashboard.py:332-343` never checks that the checkpoint contains artifacts omitted from the interrupt. Human review can therefore hide evidence, screening, allocation and explanation while a resume decision targets the full saved workflow. This is the same root cause and remediation as ARCH-01, not an additional finding. Scope remains local corrupted/replacement presentation state; no remote exploit or trade execution is claimed.
