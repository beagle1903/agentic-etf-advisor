# Bounded catalogue research in the local dashboard

Choose **US / EU catalogue research** in the advisory scope. Preview a pinned
direct-listing scope using region, country, exchange, text or exact listing IDs.
The preview reports discovered, direct, direct-only, overlap, combined,
matched and requested counts, plus the provider-partition status and
unsupported-country/venue limits. A request over 100 or an empty match is
rejected with counts rather than truncated. An over-limit preview shows the
measured matched count and effective limit so the user can narrow it; unexpected
source or parser failures show a fixed diagnostic without raw provider text.
Pages are display-only. Directory
coverage is based on the fixed Yahoo partitions and is not a claim of every
ETF or of usable research.

Start a job with up to ten existing local reference-fact files, if needed.
**Collect next catalogue batch** runs up to five listings per click and saves
each successful record. On failure, inspect the failed listing and use its
explicit exact retry; saved successes are not refetched. A job can be reopened
by its local manifest under `.artifacts/catalogue-research`. Requests are
limited per attempt, including HTTP count, timeout, received bytes and overall
deadline. The panel distinguishes requested, researched successful, pending,
failed, generation, finalized and publication state. A stopped job does not
imply a published snapshot.
The bounded Yahoo attempt restores the ordinary research session after either
success or failure; a later review cannot inherit an expired attempt budget.

When all requested records are cached, **Finalize complete catalogue snapshot**
checks their unchanged source times and creates one canonical ingestion time.
It may reject a long-running job whose observations aged out. **Publish complete
catalogue snapshot** stages the whole payload through the existing local
evidence stores and activates only after complete readback. If acknowledgement
is lost, refresh the job and verify the store before retrying; do not infer
rollback. **Use published scope for new review** pins that snapshot to an
evidence-enabled new review. Existing saved reviews keep their own identity.

The review shows requested evidence and health for every listing, screening
reasons, usable count before shortlisting, the at-most-ten shortlist, and the
final model portfolio. The selection report distinguishes omissions, unknown
and not-evaluated counts from zero, and gives one reason per requested listing.
Missing source fields, unsupported category, stale facts, economic-group
conflicts and exclusions remain visible. A ready portfolio is
illustrative and may omit a full-pool feasible alternative because shortlist
selection is bounded. Source observation timestamps are preserved; finalization
and review do not turn old source facts into fresh ones. Yahoo data is suitable
only for local research under the project's data-source boundary.
