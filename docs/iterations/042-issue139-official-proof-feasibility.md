# Issue 139: official Fund proof source feasibility

Issue 139 generation 1 (`115d9bcf9d5f05e4890efb954d9328696b3c308553d3bb653685bfec0fbda114`) authorized one evidence-only pass for the documented VWCE, CSPX and BND leads. The ordinary implementation owner `/root/issue139_owner` used only the ignored `.artifacts/issue139-source-feasibility/` scratch directory. No catalogue, registry, key, pointer, market or Issue 123 state was changed. This is an availability result, not financial eligibility or legal Fund certification.

## Offline preflight and acquisition

The local preflight passed before external I/O. It checked Bing `/ck/a` URL decoding as discovery only; exact URL, HTTPS and hostname admission including redirect targets; HTTP 200 challenge-page detection; the pinned yfinance 1.7.0, curl-cffi 0.16.2 and loaded `libcurl/8.21.0-IMPERSONATE` transport; a real loopback native `CURLOPT_MAXFILESIZE_LARGE` boundary at 1,024 and 1,025 bytes; and a deadline check after a durable start marker. The live reader used zero retries, disabled automatic redirects and reserved/logged each URL before I/O. No search call was made. The ignored raw body and JSONL log retain the sole attempt; the terminal record was not reset.

The durable start was `2026-11-04T13:31:55.123172Z`; the first exact URL was reserved at `13:31:55.131969Z`. Its deadline was 15 minutes from start, with remaining time recalculated after the fsynced start and each fsynced attempt marker. The pass ended at `13:32:02.294969Z` after 7.172 seconds. Limits and measured use:

| Budget | Limit | Use |
| --- | ---: | ---: |
| Official-domain searches | 4 | 0 |
| Issuer/exchange attempts, including failed calls and redirects | 8 | 2 |
| Per request | 15 seconds | 5.54 seconds for VWCE; 1.61 seconds for CSPX, from adjacent logged timestamps |
| Per response body | 2,097,152 bytes | VWCE 438,311; CSPX native curl size error 63, with no saved body |
| Aggregate admitted body | 16,777,216 bytes | 438,311 exact successful bytes; the failed CSPX transfer has no callback count in the durable log, so conservative upper bound is 2,535,463 bytes |
| Total window | 900 seconds | 7.172 seconds |

The logged aggregate `bytes` value counts complete responses only. The failed second response's exact delivered-byte count was not retained; its pinned native response ceiling bounds the conservative aggregate above. It is therefore **unknown**, not zero. Curl error 63 is a native size rejection, so the second source is inaccessible under this envelope. The stop rule prevented a third request and any alternate URL or retry.

## Source-to-proof matrix

The intended field for each exact URL was frozen in its durable pre-request record. Search results and historical leads were not promoted into current proof. A response `Date` is the collection-time server header, not an original observation time for legal identity or class membership.

| Lead | Exact official source and result | Attributable locator and time | Proof coverage and gap |
| --- | --- | --- | --- |
| VWCE, growth | [Deutsche Börse listing](https://live.deutsche-boerse.com/en/etf/vanguard-ftse-all-world-ucits-etf-usd-accumulating?currency=EUR), HTTP 200, 438,311 bytes, SHA-256 `3aa08ab6a6aa12a0ce7deab553719ae56d5533b562e5c3b1660c6b09ecb3df18` | Saved HTML `01-VWCE.body`, embedded `path_\\u002Fdata\\u002Finstrument_information_params_slug=...` object: `exchangeSymbol=VWCE`, `isin=IE00BK5BQT80`, `mainCurrency=EUR`, `defaultMic=XETR`, `mics=[XETR,XFRA]`; visible Master Data row `Trading currency EUR`. Collected `2026-11-04T13:32:00.672681Z`; server `Date: Wed, 04 Nov 2026 13:32:00 GMT`. Embedded `timestampLastPrice=2026-11-04T14:16:48+01:00` applies **only to price**, not legal identity. | Supports the exact listing/class ISIN and EUR trading currency as returned. The page's `issuer` field is `null` in the data-sheet-header object. It does not establish legal Fund identity, complete current class inventory, active membership, continuity or original current observation time for those proofs. |
| CSPX, growth | [iShares product lead](https://www.ishares.com/uk/individual/en/products/253743/ishares-core-s-p-500-ucits-etf?siteEntryPassthrough=true&switchLocale=y), request 2 failed with native curl error 63 before a complete response was available. No saved body or hash. | Reserved `2026-11-04T13:32:00.676933Z`; error logged `13:32:02.283334Z`. No trustworthy response status, source locator or source observation time. | Legal Fund, exact Amsterdam venue/class, active class membership, inventory and continuity remain unsupported. Historical page references are discovery leads only. |
| BND, defensive | [Vanguard product lead](https://advisors.vanguard.com/investments/products/bnd/vanguard-total-bond-market-etf) was **not requested** after the mandated stop. No body, hash, current observation or collection time. | Historical lead in the pre-approved Issue 123 direct-source recovery decision only. The separate BND/NMS diagnosis and NGM observation were not revalidated. | Current legal Fund, exact class/venue, active membership, inventory and continuity remain unsupported. |

The result cannot support a credible complete route for three distinct legal Funds across growth and defensive sleeves. It supplies one listing-level observation, one oversized official page and one unrequested lead. No Fund/class equivalence, active status, continuity or eligibility is inferred. Further source work, a different exact document, or a new operational Issue 123 design requires separate authority; this one-pass result does not reset the earlier attempt or authorize publication.
