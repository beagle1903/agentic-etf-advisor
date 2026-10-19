# Issue104 explicit model exception

On 2026-10-19 the user requested in this chat: "or switch to sol 6.1 med".
After repeated gpt-6-sol capacity failures, this explicitly selects
gpt-6.1-sol/medium for remaining implementation-owner work on Issue104 only.
The coordinator interrupted the old live owner before the replacement.

Actual fresh sequential successor execution session:
`/root/issue104_owner_sol61`, gpt-6.1-sol/medium, performing the authorized
implementation_worker responsibilities. Original actual execution session:
`/root/issue104_owner`, gpt-6-sol/medium. Both are implementation/verification
authors and excluded from independent review. No concurrent implementation.

The existing logical ledger reservation `/root/issue104_owner` continues with
all consumed counts retained. The native ledger cannot encode per-ticket model
exceptions: its pinned owner metadata remains the original logical reservation,
not an assertion of successor model or live-session identity. Actual provenance
is recorded here, in the issue/PR and ledger evidence. No generic workflow tool
or role config is changed. This is the explicit one-off workflow exception
authorized by the user, not an additional implementation slot or design reset.

Generation2 frozen scope, owner responsibilities, financial rules, interfaces,
approved handoff hash and verification/acceptance/independent review/delivery
requirements remain authoritative. No additional allowance or product scope.
