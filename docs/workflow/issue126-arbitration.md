# Issue126 coordinator arbitration A126-1

- Opened: 2026-10-27T04:52:17Z; coordinator `/root` under the human's Issue126
  implementation authorization and AGENTS/ADR0034 internal arbitration authority.
- Frozen capsule: issue-126-audited-curator-fund-identities, generation1,
  `c50e07ba8308449c2f0fd402de5f1a94aafe8cf7d38bb598363d349626be3335`.
  Repository content is still mutable in the original implementation pass; no
  verification, acceptance, review or delivery certificate exists.
- Trigger: owner self-review proposed treating suspended-to-active as `refresh`
  after discovering that `suspend` falsely describes that change; this proposes a
  lifecycle remedy not explicitly defined by the frozen handoff. A second owner
  report exposed collection after registry recording in a synthetic fixture.
- Earlier response/closure: no prior adjudication of either scenario. No reviewer
  finding, failed review or design-reset outcome is being relabeled.
- Phase/reservation: original `/root/issue126_owner` implementation_worker/
  gpt-6-sol/medium implementation reservation remains active, count1 of1.
  Initial review1, remediation1, final review1 and design reset1 remain. No new
  dependent handoff or certification until this decision's focused closure.
- No phase interruption is needed: the owner continues unrelated tests/docs and
  then performs these same-scope guards in the existing active pass. This dispatch
  hold is not a coordination_pause; all elapsed audit time remains counted.

| Role/session | Frozen IDs | Scenario and evidence | Classification |
| --- | --- | --- | --- |
| Owner `/root/issue126_owner` | INV126-2, AC126-1/2 | `validate_publication` derives `refresh` for suspended-to-active despite no explicit resumption contract; earlier `suspend` label also described the opposite state change. The design's allowed operation list and explicit suspend/retire requirements do not specify resumption. | Proposed capability outside the defined lifecycle transition contract; accepting an unsupported change is a demonstrated fail-closed gap. |
| Owner `/root/issue126_owner` | INV126-2, AC126-2 | A source's collected_at is later than its enclosing recorded_at in a synthetic fixture. Published registry content cannot truthfully contain evidence not yet collected; parent generations must not run backwards. Current checks allow both. | Demonstrated chronology gap within the frozen source-chronology/attestation and retained-generation requirements. |
| Architect `/root/issue126_design`; independent challenger `/root/issue126_challenge` | INV126-2/3 | Handoff036 requires source chronology, immutable generations, actual-parent derivation and rejection of unsupported changes. Handoff035 lines166-184 specifies lifecycle operations and retained history, with no resumption procedure; current-proof C(F) freshness is separately fixed. | Existing contract evidence; neither role previously approved a resumption procedure or chronology exception. |

## Accountable decision: narrow repair

Keep unsupported suspended-to-active publication fail-closed for Issue126. Do not
invent a resume operation or reinterpret refresh as authority to restore active
eligibility. This issue requires suspension safeguards, not a new resumption
workflow. Reject that attempted change before publication, retain the suspended
key/history, and document the implementation limitation. Retired resurrection also
continues to reject. A later request for resumption needs a separately specified
contract under its proper authority; this record neither grants nor designs it.

Enforce the existing chronology contract narrowly: every retained source's
collected_at and the audit's attested_at must be no later than the envelope's
recorded_at; child recorded_at must be no earlier than the actual parent.
Keep existing source-internal chronology and five-minute future guards. Equal
timestamps are valid. These are ordering checks on declared audit events, not
source/actor authentication. Do not add effective-date, publication-date,
observation-expiry or new clock rules by analogy.

The inclusive C(F) source window remains exactly unchanged. Synthetic future-edge
fixtures must use coherent collection/attestation/recording coordinates rather
than weaken that window or renew source observations. Historical-only lineage
still has no age expiry.

Rejected alternatives: silently authorize resumption through refresh; label
activation as suspend; waive chronology because fixtures currently pass; expand
the operation schema; or obtain extra agent agreement without a reserved phase.
No frozen AC demands resumption, and the chronology gap has a concrete impossible
audit path, so these narrow guards resolve this episode without changing the
frozen definitions or consuming a design reset. The owner's initial resumption
reading is retained above as disagreement, not erased. New evidence of an
incompatible explicit frozen requirement must return to this episode before any
dependent handoff; genuine unresolved consequential ambiguity would still require
the separate architect/challenge/approval gates within finite allowances.

## Focused closure and next gate

Owner `/root/issue126_owner` adds focused negative tests proving that a valid
suspended parent cannot publish an active child under refresh (or suspend),
source collection/attestation after recording rejects, and parent recording cannot
go backwards. Positive same-status refresh/suspension/retirement behavior and each
inclusive C(F) freshness edge remain covered with coherent timestamps. Run the
focused identity tests and current required checks; finish the limitation and
chronology documentation before content-bound certification. Same owner and same
implementation reservation; no new phase/count authority.

Closure evidence remains pending. Once these guards/tests/docs pass, coordinator
records closure in the excluded current-ticket ledger evidence and may close the
implementation phase, reserve owner verification, acceptance and independent
initial review in order. Episode closure is not ticket acceptance or delivery.
