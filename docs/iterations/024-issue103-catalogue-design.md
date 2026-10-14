# Issue 103 catalogue design handoff

Architect: `/root/issue103_design`, `design_architect`, `gpt-6-astra`, high.
Issue [#103](https://github.com/beagle1903/agentic-etf-advisor/issues/103), parent
[#24](https://github.com/beagle1903/agentic-etf-advisor/issues/24).
Frozen capsule `issue-103-yahoo-catalogue`, generation 1, digest
`552e8871276002b83388d4b8867bbdae0d27e543f831194a41faf857ca440b83`.
Owner: `/root/issue103_owner`, implementation_worker / gpt-6-sol / medium.
Architect returned DESIGN_READY; independent challenge and coordinator approval are
required before implementation. This document records the returned handoff.

## Source capability and measured evidence

The lock pins yfinance 1.7.0; the project environment lacked this optional package.
The architect imported the existing cached distribution via process-local sys.path,
disabled bytecode, and replaced persistent cookie/timezone caches with in-memory
no-op boundaries. No installation or persistent probe artifact was created.
Official [ETFQuery](https://ranaroussi.github.io/yfinance/reference/api/yfinance.ETFQuery.html),
[screen](https://ranaroussi.github.io/yfinance/reference/api/yfinance.screen.html), and
[Search](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Search.html)
documentation and cached 1.7.0 code establish API capability, not completeness.

Live probes on 2026-10-14 around 08:01-08:04 UTC returned:

| Partition/query | Observation | Limit |
|---|---|---|
| us/PCX | offset 0 and 2, size 2; total 2671 | Two pages only |
| de/GER | same offsets/size; total 6142 | Two pages only |
| nl/AMS | same offsets/size; total 740 | Two pages only |
| pl/WSE | offset 0, size 250, count/total/rows 57 | One returned partition |
| ro/BVB | offset 0, size 250, count/total/rows 11 | One returned partition |
| SCHD, VWCE.DE, CSPX.AS | exact ETF results, PCX/GER/AMS | Direct identity capability |
| VUSA.L, SWDA.SW | ETF, LSE/EBS | Excluded listings |
| AAPL | exact EQUITY plus unrelated ETF suggestions | Must reject exact lookup |
| ZZZZZZ103UNKNOWN | empty | Unknown lookup |

No tested call failed. Other partitions are live-unverified; no complete US/EU
catalogue was collected. Search returned no regularMarketTime or currency.
Catalogue observation time means adapter observation of the response; an optional
source quote time remains a separate nullable field. Never invent a market time.
Yahoo classified some WSE ETN/ETC-named symbols as ETF: retain provider classification,
without certifying regulatory identity or eligibility.

## Boundary and mapping (INV103-1, INV103-5)

Build beside cli.publish_research_universe -> load_research_universe ->
YahooResearchAdapter.fetch_snapshot -> existing canonical research publication.
Do not replace packaged membership or publish discovered records to research stores.
CandidateEvidence.require_us_market and domain.screening remain unchanged.
No EU eligibility, ranking/allocation/optimizer, all-ticker rich research, scraping
completeness, authentication/hosting, trades/financial writes, or Issue104/105 work.

Package mapping version `yahoo-listing-map-v1`; classify only source exchange code,
never currency, suffix, domicile, fund name or holdings. The current EU membership
is corroborated by the [EU Member States list](https://eur-lex.europa.eu/EN/legal-content/glossary/member-states.html).

| EU country | Yahoo codes |
|---|---|
| Austria | VIE |
| Belgium | BRU |
| Czechia | PRA |
| Denmark | CPH |
| Estonia | TAL |
| Finland | HEL |
| France | ENX, PAR |
| Germany | BER, DUS, EUX, FRA, GER, HAM, HAN, MUN, STU |
| Greece | ATH |
| Hungary | BUD |
| Ireland | ISE |
| Italy | MDD, MIL, TLO |
| Latvia | RIS |
| Lithuania | LIT |
| Netherlands | AMS, DXE |
| Poland | WSE |
| Portugal | LIS |
| Romania | BVB |
| Spain | MAD, MCE |
| Sweden | STO |
| Bulgaria, Croatia, Cyprus, Luxembourg, Malta, Slovakia, Slovenia | Unsupported: no mapped exchange |

US codes: ASE, BTS, CXI, NAE, NCM, NGM, NMS, NYQ, PCX.
Exclude US OTC/deleted buckets OEM, OQB, OQX, PNK, YHD; UK AQS, CXE, IOB,
LSE; Swiss EBS; all other non-US/non-EU and unknown codes.
The fixed manifest has 42 partitions: 33 EU and 9 US. Mapping changes require a
new map version and reviewed contract. Unsupported countries mean unsupported,
never zero actual ETFs. Record excluded/unsupported reasons explicitly.

## Listing identity and records (INV103-1 through INV103-3)

Identity is (yahoo_finance, exact normalized Yahoo symbol, exchange code), encoded
deterministically or digested. Trim/uppercase input; preserve suffixes and punctuation.
Reject controls, internal whitespace and unreasonable length; do not use the existing
research-universe symbol-length restriction. Cross-listings remain separate even
when names or identifiers match. Optional underlying identity is scheme/value/source
URL/observation time or explicit absence; v1 need not fetch one. Never infer ISIN or
merge by names, stripped suffixes or fund family.

Required fields: listing ID, provider symbol, quoteType ETF, exchange, derived country
and region, mapping version, display name or not_reported, nullable currency/underlying
ID with missing reasons, provider, endpoint/quote URL, response UTC observation,
nullable source quote time, partition/page or exact-lookup provenance, entry origin,
immutable catalogue version. Persist allowlisted normalized fields only; no raw
responses, secrets, cookies or raw exception text. No financial metrics needed.

## Discovery (INV103-2; AC103-2, AC103-4)

For every manifest partition use ETFQuery(and, [eq(region, lower-case-country),
eq(exchange, code)]); custom screen size250, offsets0,250,..., sortField ticker,
sortAsc true. Record actual serialized query and source/library/map versions.
No price, rating, liquidity or other economic filters; no top screen or Search directory.

Bounds: 40 pages / 10000 provider rows per partition, 256 logical page attempts
including retries per refresh, two attempts per page, 300-second refresh deadline.
Bound underlying HTTP to ten seconds and remaining deadline, including authentication.
screen has no public timeout: injected transport must enforce bounds without silently
changing global Yahoo retry settings. Any exhausted bound yields incomplete.

Validate exact nonnegative integer start/count/total (not bool), start=requested
offset, count=received rows<=size, identical totals across pages, each row valid
ETF identity and requested exchange. Short/empty page before total is incomplete;
received totals must reach declared total without exceeding it. Count/deduplicate
duplicate identities diagnostically; complete requires unique identity count=total.
Conflicting duplicates fail. total0/start0/count0/rows0 is a valid empty provider
partition, without claiming absence of actual listings.

Per-partition evidence: status/query/request-response times, every offset/count/total,
normalized identity digest, unique/duplicate/rejected counts, retry/error codes,
truncation reason. Failed/unattempted partitions remain visible. Full refresh may
publish only if every manifest partition completes. Endpoint rejection never removes
a partition. Label `provider_partitions_complete`, never all_yahoo_etfs or all EU ETFs
or atomic market snapshot. Stable totals cannot detect all upstream omission or
same-count mutation. Unsupported countries/excluded venues remain coverage limits.

## Search and direct lookup (INV103-3; AC103-3)

Local symbol/name search returns version/cache age/matched count/output limit.
Optional live suggestions use Search max25 quotes, no news/lists/recommendations,
fuzzy disabled; label non-exhaustive, no automatic publication or discovery completion.
Exact lookup considers only exact normalized symbol matches; require one unambiguous
ETF result with accepted exchange. Reject non-ETF/unknown/disallowed/conflicting or
merely similar matches. AAPL never resolves to an AAPL-related ETF.

Publish verified additions as new immutable versions; return verification and
publication outcomes separately. Failed local publication is not an addition.
Search provider_total=null/not_reported; returned match count is distinct.
Missing source quote time remains null. A first direct addition creates direct_only
with discovery not_run. Addition to a prior version preserves discovery report and
original full-refresh time; never makes discovery fresh/complete.
Full refresh replaces discovered component, retains separately labelled direct
additions with original observation times, never relabels them newly enumerated.
Conflicting refreshed identity versus retained direct record fails publication,
without silent merging or relocation.

## Cache/publication (INV103-4; AC103-5)

Separate replaceable page/search/lookup provider, catalogue operations, clock/deadline
and persistence interfaces. New catalogue package, Yahoo adapter and thin CLI commands;
existing research interfaces unchanged. Ignored `.artifacts/catalogue/` storage:
strict schema JSON immutable blobs, content-addressed version from canonical validated
JSON excluding derived digest/version fields, parent version/operation/map-query
manifest/records/coverage/timestamps, small atomic active pointer.

Readers validate pointer/exact schema/digest/count and identity relationships;
reject duplicate JSON keys and nonfinite values. Collect outside publication lock.
Bounded cross-process exclusion and CAS against parent captured before collection;
competitor yields explicit conflict, never automatic merge or overwrite. Write/flush/
validate immutable blob before atomic pointer replacement. Interrupted staging may
leave unreachable blob but cannot replace prior catalogue. Do not auto-remove
supposed stale locks.

Read cache without network. Full refresh cache reuse24h; force bypasses reuse only,
never validation/bounds. Expired catalogue supports explicitly stale search/discovery.
Failure/incompleteness returns report alongside unchanged prior version, or unavailable
if no prior version. Corrupted active payload fails closed, never fresh empty.
Direct-only cannot satisfy full-refresh cache; direct additions do not reset its age.
No pruning, migration or research publication.

## State, acceptance and documentation

New catalogue JSON only; graph/checkpoint, research schema1/2 and snapshot identities
unchanged. Runtime clients/locks/clocks remain outside serialized state. Report
discovered/direct/combined listing counts separately. Researched/eligible/shortlist
counts are not derived, and must not be misleading catalogue counts or zeros.
Preserve Issue99 frozen dataset identities and metric meanings.

Focused fixtures mapped to frozen IDs:

| IDs | Positive and negative verification |
|---|---|
| INV103-1; AC103-1/3 | US, German EUR, Dutch USD; Irish domicile/UK rejected; Swiss/UK/unknown rejected; every mapping code/country; seven unsupported countries; OTC/deleted excluded |
| INV103-2; AC103-2/4 | Multi-page, exact-multiple, zero partition; malformed/bool totals, wrong offset/count, short/empty, increasing/decreasing totals, errors, deadlines/attempt/page limits, unattempted partitions |
| INV103-2/3; AC103-4 | Within/across-page duplicate and conflicting duplicate; distinct suffix IDs with same names; non-ETF/unknown exchange in screen fails candidate |
| INV103-3; AC103-3 | Outside-six valid symbol, DE/AS preserved, no exact match, AAPL alternatives, conflicting exact results; absent time/currency/underlying stays absent |
| INV103-4; AC103-5 | Fresh zero-call reuse, expired/forced fetch, failed refresh prior bytes/pointer, first failure unavailable, direct-only, addition age, refresh retention/conflict |
| INV103-4; AC103-5 | Corrupted JSON/digest/schema, blob/pointer failure, interrupted stage, two CAS writers, bounded lock timeout, no last-writer overwrite |
| INV103-5; AC103-5 | No research/graph publication calls, existing EU rejection, unchanged packaged six and full Issue99 baseline |

Fixtures are synthetic, distinct from measured live probes. Owner runs workflow
validation, lint/format, full pytest, evaluate-analysis and applicable type gates.
Create catalogue ADR/active iteration record; update architecture and CLI usage with
mapping/version semantics, observation versus quote time, stale/direct-only states,
failure behavior and actual coverage limitations. Preserve accepted ADR history and
US-only product/advisory scope.

Residual risks: Yahoo taxonomy errors, unavailable/misbehaving partitions, silent
omissions, same-count mutation and local contention. Handle with attributable
classifications, bounded fail-closed publication and explicit coverage limits.
No demonstrated source blocker. Independent challenge tests concrete pagination,
direct age/identity conflict and publication races against frozen IDs before approval.

## A103-1 generation 2 clarification

Fresh architect `/root/issue103_design_reset`, gpt-6-astra/high, returned the
following supplement within INV103-3/4 and AC103-3/5. The initial failed challenge
remains failed. This supplement requires fresh independent challenge and approval.

Each catalogue version contains separate `discovered` and `direct` observation
components, each with at most one validated observation per listing identity.
Intersection represents two observations of one listing. Full refresh replaces
only discovered after all42 partitions complete, copying direct observations exactly:
missing reasons, source URLs, lookup provenance, response times and quote times.
Creation/publication time never substitutes for observation time.

Combined projection selects the whole discovered observation when present, otherwise
direct. This is component precedence, not a claim of timestamp recency. Never merge
fields. Each combined result exposes listing ID, containing version, both origins if
overlapping, selected origin and selected observation time/provenance. Both original
observations remain in validated catalogue audit data; containing version does not
relabel when direct data was collected.

| Scenario | Deterministic rule |
|---|---|
| Same identity, identical optional values | Publish with both observations, one combined listing, discovered authority |
| Same identity, changed name/currency/underlying identifier/quote time | Valid differing observations, not identity conflict; preserve both and select entire discovered observation |
| Discovered lacks optional value present in direct | Return discovered explicit absence; no backfill |
| Discovered has value absent in direct | Return discovered value/provenance; retain direct absence |
| Direct identity absent from completed discovery | Retain direct-only, original observation; absence does not prove delisting |
| Discovered identity absent from direct | Return discovered only |
| Same provider/exact normalized symbol with different exchange codes in candidate union | Reject publication as source-identity conflict even if both exchanges allowed; preserve prior active version, no relocation or dual interpretations |
| Distinct symbols/suffixes with same name/underlying identity | Separate listing identities |
| Invalid required identity/type/exchange/ID/derived mapping | Reject; no fallback to conceal failure |
| Incomplete/conflicting/failed publication or CAS | Prior version remains active; failed attempt report separate from active projection |

Optional differences must each be valid values or explicit valid absences, not
malformed values/provenance/time. Different valid URLs, response/quote times or
page/lookup provenance are independent observations, not identity conflicts.
Within-attempt conflicting discovery duplicates and conflicting exact lookup matches
still fail under the original rules.

`discovered_count=|D|`, `direct_count=|L|` including overlap,
`combined_count=|D union L|`; counts are not additive. Optional overlap count=intersection,
direct-only count=L minus D. Direct/combined counts never contribute to provider
partition totals, completion or freshness. If serialized, projections/counts are
recomputed and validated; canonical binding covers both observation components.

Local search matches the combined exact symbol and selected display name, each listing
once, matched count before output limit. Superseded direct names do not independently
match while discovery has precedence. Exact lookup returns actual verification
observation separately from publication outcome and active projection; verification
does not imply publication or selection of that lookup observation by local search.

Required synthetic42-partition fixture (only GER nonempty): T0 direct VWCE.DE/GER
Old name, currency null/not_reported -> direct-only0/1/1. T1 discovered same identity,
New name/EUR -> successful1/1/1, both origins, discovered whole observation/T1 selected;
original direct Old name/null/T0 lookup observation unchanged. T2 discovered missing
name/currency -> publish explicit absences without backfill; direct unchanged. Later
complete discovery absent ->0/1/1 direct originalT0 authority. From overlapping version,
valid VWCE.DE/FRA -> identity-conflict failure with prior pointer/payload unchanged.
Distinct suffixes remain separate; search overlap deduplicates; cross-component optional
differences succeed while conflicting duplicates within discovery fail.

Graph/checkpoint and research schemas remain unchanged. Catalogue operations expose
pure validated combined projection and separate outcomes; runtime dependencies stay
outside JSON. Document these rules in ADR/iteration/CLI guidance. Residual risks:
discovery precedence can expose missing values despite populated direct observation;
true exchange reassignment blocks publication pending separately authorized handling.

## Coordinator approval

Generation2 effective capsule digest
`b9c97b4c7f067883a8752c7b8846b9cb63c85ca5848c926e3567542074b7a234`
includes the clarified interface and catalogue JSON state definitions. Fresh independent
`/root/issue103_challenge2`, code_reviewer/gpt-6-sol/high, returned PASS with no frozen
criterion blocker. Coordinator `/root` approves initial handoff plus supplement on
2026-10-14, closes A103-1 and authorizes the native implementation gate for unchanged
owner. User continue authorizes this selected Issue103 scope; no additional phase
allowances, eligibility changes or next-child work are implied. Native ledger records
the separate failed challenge, counted reset, successful challenge and approval.
