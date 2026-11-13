# ADR 0051: Separate model presets from task assignments

- Status: Accepted for Issue 109
- Date: 2026-11-13
- Supersedes: ADR 0025's prospective six-role model/effort registrations and ADR 0049's configuration-only validator description. Historical records and the rest of those decisions remain intact.

## Context

Six project agent registrations duplicated model selection across responsibilities. Issue 109 proposed three model presets and separately declared task assignments. Separate architect advice, [coordinator approval](https://github.com/beagle1903/agentic-etf-advisor/issues/109#issuecomment-6849362501), and the user's [instruction-only access amendment](https://github.com/beagle1903/agentic-etf-advisor/issues/109#issuecomment-6849027730) resolved the prospective contract. A bounded v2 comparison selected Luna medium before these configuration edits; both efforts passed all three tasks after at most one repair, while medium had fewer first-pass defects and repairs. Usage was unavailable, and observed orchestration time is not isolated model latency.

## Decision

Register only `astra` (`gpt-6-astra`/high), `sol` (`gpt-6.1-sol`/medium) and `luna` (`gpt-6-luna`/medium) with explicit descriptions and relative `agents/<preset>.toml` files. These choose model and effort only. A fresh dispatch separately declares assignment, activity, scope, permitted actions, acceptance, participant and owner references, rationale, authorization, consequential status, observed inherited access, and `restriction_kind=instruction-only`. Owner is accountability, not a fourth preset. The six former role names remain assignments rather than registration names.

Discovery, design, review and optional challenge are inspect/report only. They prohibit edits, mutating commands, external actions and delegation regardless of inherited parent access. Implementation, remediation and verification belong to the three writer assignments; verification does not edit. A writer participant equals the owner and may declare delivery responsibility for commit/push/PR actions. Consequential design advice remains separate from the owner, consequential writes require coordinator approval, and review is independent of the owner and every implementation, remediation and verification author. An optional challenge is separate from its design author. It is not a required phase. Dependent handoffs remain sequential; independent code review still follows consequential work under ADR 0049.

The existing validator checks exact preset configuration without depending on docs, ledgers or cwd. Its optional `--declaration PATH` input checks internal JSON consistency and reports errors without a traceback. It does not dispatch agents, store declarations, authenticate identities or approval references, inspect live tools, or enforce filesystem access. A coordinator must check actual authorization, participants and inherited access. No custom launcher, sandbox claim or mandatory process engine is introduced.

ADR 0018's prohibitions on generic model defaults, project-level model overrides, `enabled`, concurrency scalars, `max_threads` and default role remain. Historical tickets, prior role/model/effort identities, consumed events and delivery outcomes are never migrated or relabeled. Existing Issue 109 bootstrap implementation and independent review sessions retain their original selected role/model/effort. Product, finance, providers, external writes and graph/checkpoint JSON are unchanged.

## Limits

Instruction-only restrictions are not an access-control boundary. A declaration can be internally valid and factually false; the optional checker cannot establish actual model identity, session independence, approval or a runtime registration reload. The CLI account rejected model inference during capability probes; app-native requested settings produced the comparison and design advice, without independent backend attestation. The current parent has not demonstrated loading the newly named preset registrations. Issue 109 acceptance requires independent code review and final verification; this ADR records the approved contract, not a claim that those gates passed.
