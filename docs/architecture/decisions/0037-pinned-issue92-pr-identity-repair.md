# ADR 0037: Pinned Issue92 live PR identity repair

Status: Accepted for the exact finite Issue92 disposition approved on 2026-10-09.

The failed independent initial review found that CI compared only the live head
SHA and then reused the queued head branch and repository. Equal commits can
belong to different branches or forks. CI now validates complete queued and live
PR identities and uses the validated live head, base, creation time and body.
Issue92 additionally requires its granted repository and branch, original PR
target, and creation after the latest disposition grant. Ordinary matching fork
PRs retain their existing eligibility.

The immutable sixteen-event failed-review stop and approved
`issue-92-pr-identity-repair-v1` package authorize only event 17 and an immediate
same-owner remediation start at event 18. The earlier fixture recovery remains
failed and its initial review remains consumed. This separate disposition grants
one sixth remediation, one third local verification, and one fifth **final**
review. Fresh verification, complete acceptance and a clean independent final
review must bind the repaired content before the original unused publication
target and delivery sequence. Any completed failure stops the new disposition.

The complete 43-source and eight-closeout descriptors, both earlier archives,
grant and proposal digests, authority identity, historical prefix and author
exclusions are pinned. The pre-validator append of events 17 and 18 was the
single explicitly approved bootstrap exception; native validation of the saved
pair is required before closing remediation. No prior failure, count, capsule,
source, content or PR binding is rewritten. This ADR supplements ADRs 0035 and
0036 only for the exact post-review Issue92 state.
