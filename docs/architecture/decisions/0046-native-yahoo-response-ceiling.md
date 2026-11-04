# ADR 0046: Native Yahoo response ceiling

- Status: Accepted for Issue 137 implementation after separate architect, independent challenge and coordinator approval.
- Date: 2026-11-04
- Authority: Issue 137 generation 1 capsule `1714e87eb713bee96c02bacbc0c6535ce07da6b0726f7f3d7faa46c2dfd53998`.

The existing Python callback checked the byte total only after curl-cffi had copied a complete chunk into Python. Its ordinary zero return on overflow was also translated by curl-cffi 0.16.2 into a full-chunk success return. An attempted two-megabyte limit could therefore receive at least one byte beyond the approved ceiling before reporting failure.

Use libcurl's `CURLOPT_MAXFILESIZE_LARGE` on every bounded Yahoo request. The reviewed libcurl 8.21.0 implementation limits body bytes before forwarding them to the Python callback, including decoded bodies and transfers without a declared length. The supported runtime tuple is yfinance 1.7.0, curl-cffi 0.16.2 and the loaded native version token `libcurl/8.21.0-IMPERSONATE`. Unknown tuples fail before a request. A trusted locked installation is assumed; a malicious binary misreporting that identity is outside this local development contract. [libcurl option reference](https://curl.se/libcurl/c/CURLOPT_MAXFILESIZE_LARGE.html)

The bounded session owns the effective native options and refreshes them for each request after user settings and impersonation. It forces the size cap, ordinary body-only callback, no debug callback, HTTP/HTTPS protocols and redirects, and content and transfer decoding. It uses zero retries. The existing Python callback remains a defensive byte and deadline check, returning `CURL_WRITEFUNC_ERROR` for a breach. Native size error 63 marks the budget breached and returns the existing Yahoo budget failure without publishing partial bytes.

The ceiling counts cumulative response body bytes reaching the Python body callback. Native socket, TLS and decoder working buffers, and later copies of already admitted bytes, are distinct. Libcurl skips intermediate redirect bodies on an automatic follow. It may reject a declared oversized intermediate response before following. Exact complete final bodies remain usable.

Offline loopback tests exercise exact and crossing bodies, known and unknown lengths, chunked and gzip expansion, redirect final bodies, version and cap rejection, option refresh, retry and deadline abort. No provider traffic is needed for this contract. Product graph, checkpoint and persisted research JSON are unchanged.
