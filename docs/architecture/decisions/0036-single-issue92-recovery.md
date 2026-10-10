# ADR 0036: Single counted Issue92 fixture recovery

- Status: Accepted for the exact Issue #92 recovery grant
- Date: 2026-10-09
- Supplements: ADR 0035 for one failed Issue #92 verification; preserves ADRs 0026, 0033 and 0034.

The first full Issue92 verification failed because six tests used the mutable live
ledger as a historical fixture. After the legitimate verification reservation, those
tests assumed implementation was still active or appended older synthetic events.
The failure and blocker `B92-LIVE-LEDGER-FIXTURE-DRIFT` remain recorded.

The user approved one same-owner counted remediation and one fresh verification.
The exact six-event stopped prefix, complete immutable recovery sources, independent
R92D1/R92C1 design and challenge, coordinator decision and finite grant bind the
only `issue92_recovery` event. The coordinator saved that event and the ordinary
remediation start under the expressly approved pre-validator bootstrap exception.
Native replay must validate those actual saved events before successful repair.

Remediation consumes count 5/5; the second local verification consumes limit 2/2.
Inherited counts stay 4/3/4/4/4. One unused initial review and one unused new-PR
allowance are conserved. Only after successful repair, exact blocker resolution,
fresh content-bound verification and complete acceptance may the independent initial
review inspect the repaired implementation. This single pre-review repair remains a
remediation; it is not relabeled as implementation or final review. A completed
failure in repair, verification or review stops further phases and delivery.

Tests use fresh copies of the archived two-event bootstrap and six-event stop
documents. They never derive historical fixtures from the mutable current ledger.
The actual saved ledger and eventual delivered PR/content must be checked separately.
Recovery archives retain exact raw bytes in Git and participate in certification.
The original capsule, grant, past failure, authors, authority identities, historical
PR85 bindings and ADR 0035 remain unchanged. No product, graph/checkpoint, finance,
provider, database or authentication contract changes.
