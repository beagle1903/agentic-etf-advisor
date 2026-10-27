"""Synthetic curator Fund registry, proof freshness and local CAS checks."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from etf_advisor.data.fund_identity_registry import (
    LocalFundIdentityRegistry,
    RegistryCommittedCleanupError,
    RegistryPublicationError,
)
from etf_advisor.domain.fund_identity import (
    RegistryEnvelope,
    RegistrySnapshot,
    digest,
    new_key,
    resolve_group,
    validate_publication,
)

CHECK = datetime(2026, 10, 26, 18, 0, tzinfo=UTC)
REGISTRY_ID = "11111111-1111-4111-8111-111111111111"
FUND_ID = "22222222-2222-4222-8222-222222222222"
KEY = new_key(REGISTRY_ID, FUND_ID)


def _isin(prefix: str) -> str:
    stem = prefix + "000000000"
    from etf_advisor.domain.us_eu import valid_isin

    return next(stem + str(n) for n in range(10) if valid_isin(stem + str(n)))


CLASS = _isin("US")


def _at(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _context(name: str = "Synthetic Fund") -> dict:
    return {
        "issuer_legal_name": "Synthetic Issuer plc",
        "jurisdiction": "IE",
        "umbrella_legal_name": "Synthetic Umbrella",
        "fund_legal_name": name,
    }


def _source(source_id: str, observed: datetime = CHECK) -> dict:
    return {
        "id": source_id,
        "authority": "issuer",
        "provider": "synthetic_issuer",
        "url": "https://example.invalid/fund",
        "body_sha256": "a" * 64,
        "locator": f"synthetic#{source_id}",
        "observed_at": _at(observed),
        "collected_at": _at(max(CHECK, observed)),
        "effective_date": observed.date().isoformat(),
        "published_at": _at(observed),
        "publication_date": observed.date().isoformat(),
        "current_applicability": "synthetic current assertion",
    }


def _fund() -> dict:
    context = _context()
    return {
        "key": KEY,
        "status": "active",
        "context": context,
        "current_proof": {
            "fund": {"context": context, "source_ids": ["fund"]},
            "inventory": {"context": context, "source_ids": ["inventory"]},
            "memberships": [{"isin": CLASS, "context": context, "source_ids": ["member"]}],
            "current_context_links": [],
            "lineage_source_ids": [],
        },
        "aliases": [],
        "members": [{"isin": CLASS, "status": "active", "source_ids": ["member"]}],
        "lifecycle_source_ids": [],
        "related_keys": [],
    }


def _envelope(*, observation: datetime = CHECK) -> RegistryEnvelope:
    fund = _fund()
    snapshot = {
        "schema_version": 1,
        "policy": "curator-fund-v1",
        "registry_id": REGISTRY_ID,
        "generation": 1,
        "parent_digest": None,
        "recorded_at": _at(max(CHECK, observation)),
        "sources": [_source(name, observation) for name in ("fund", "inventory", "member")],
        "funds": [fund],
        "audit": {
            "curator": {
                "identity": "synthetic-curator",
                "role": "curator",
                "authorization_reference": "synthetic",
                "review_disposition": "approve",
            },
            "reviewer": {
                "identity": "synthetic-reviewer",
                "role": "reviewer",
                "authorization_reference": "synthetic",
                "review_disposition": "approve",
            },
            "attested_at": _at(CHECK),
            "compared_parent_digest": None,
            "comparisons": [],
            "transitions": [
                {
                    "key": KEY,
                    "before_digest": None,
                    "after_digest": digest(fund),
                    "operations": ["issue"],
                    "source_ids": ["fund"],
                }
            ],
            "inventory_checks": [
                {
                    "context": _context(),
                    "source_ids": ["inventory"],
                    "rows": [
                        {
                            "key": KEY,
                            "isin": CLASS,
                            "source_locator": "synthetic#member",
                            "before_status": None,
                            "after_status": "active",
                            "disposition": "added",
                            "source_ids": ["member"],
                        }
                    ],
                }
            ],
        },
    }
    parsed = RegistrySnapshot.model_validate(snapshot)
    return RegistryEnvelope.model_validate(
        {"digest": digest(parsed.model_dump(mode="json")), "snapshot": snapshot}
    )


def test_initial_registry_cross_class_proof_and_local_cas(tmp_path) -> None:
    envelope = _envelope()
    validate_publication(envelope, None, expected_parent_digest=None, checked_at=CHECK)
    assert resolve_group(envelope, KEY, CLASS, CHECK) == CHECK
    store = LocalFundIdentityRegistry(tmp_path)
    assert store.publish(envelope, expected_parent_digest=None, checked_at=CHECK) == envelope
    assert store.active() == envelope
    with pytest.raises(ValueError, match="stale registry parent CAS"):
        store.publish(envelope, expected_parent_digest=None, checked_at=CHECK)


def test_local_registry_precommit_and_acknowledgement_failures(tmp_path, monkeypatch) -> None:
    import os

    envelope = _envelope()
    store = LocalFundIdentityRegistry(tmp_path)
    original_replace = os.replace

    def fail_pointer(source, target):
        if str(target).endswith("active.json"):
            raise OSError("synthetic pointer failure")
        return original_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_pointer)
    with pytest.raises(RegistryPublicationError, match="registry_store_io_error"):
        store.publish(envelope, expected_parent_digest=None, checked_at=CHECK)
    assert store.active() is None
    monkeypatch.setattr(os, "replace", original_replace)
    original_active = store.active
    calls = 0

    def fail_readback():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RegistryPublicationError("synthetic readback failure")
        return original_active()

    monkeypatch.setattr(store, "active", fail_readback)
    with pytest.raises(RegistryCommittedCleanupError) as exc:
        store.publish(envelope, expected_parent_digest=None, checked_at=CHECK)
    assert exc.value.envelope.digest == envelope.digest
    assert original_active() == envelope


def test_local_registry_rejects_malformed_pointer_without_blob_read(tmp_path) -> None:
    store = LocalFundIdentityRegistry(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    for content in ('{"digest":"../outside"}', '{"digest":"0","digest":"1"}'):
        (tmp_path / "active.json").write_text(content, encoding="utf-8")
        with pytest.raises(RegistryPublicationError, match="registry_active_invalid"):
            store.active()


@pytest.mark.parametrize("age", [timedelta(hours=120), timedelta(hours=120, microseconds=1)])
def test_current_proof_age_boundary(age: timedelta) -> None:
    envelope = _envelope(observation=CHECK - age)
    if age == timedelta(hours=120):
        assert resolve_group(envelope, KEY, CLASS, CHECK) == CHECK - age
    else:
        with pytest.raises(ValueError, match="stale or future"):
            resolve_group(envelope, KEY, CLASS, CHECK)


def test_nonminimum_future_constituent_rejected() -> None:
    data = _envelope().model_dump(mode="json")
    data["snapshot"]["sources"][2]["observed_at"] = _at(CHECK + timedelta(minutes=5, seconds=1))
    data["snapshot"]["sources"][2]["collected_at"] = _at(CHECK + timedelta(minutes=6))
    data["snapshot"]["recorded_at"] = _at(CHECK + timedelta(minutes=6))
    data["digest"] = digest(data["snapshot"])
    envelope = RegistryEnvelope.model_validate(data)
    with pytest.raises(ValueError, match="stale or future"):
        resolve_group(envelope, KEY, CLASS, CHECK)


def test_missing_member_proof_or_tampered_digest_fails() -> None:
    data = _envelope().model_dump(mode="json")
    broken = deepcopy(data)
    broken["snapshot"]["funds"][0]["current_proof"]["memberships"] = []
    broken["digest"] = digest(broken["snapshot"])
    with pytest.raises(ValueError, match="active memberships"):
        RegistryEnvelope.model_validate(broken)
    data["snapshot"]["sources"][0]["locator"] = "tampered"
    with pytest.raises(ValueError, match="digest mismatch"):
        RegistryEnvelope.model_validate(data)
    for mutation, match in (
        (
            lambda payload: payload["snapshot"]["audit"]["transitions"][0].update(
                after_digest="0" * 64
            ),
            "transition after digest",
        ),
        (
            lambda payload: payload["snapshot"]["audit"]["inventory_checks"][0]["rows"][0].update(
                after_status="closed", disposition="closed"
            ),
            "inventory after status",
        ),
    ):
        changed = _envelope().model_dump(mode="json")
        mutation(changed)
        changed["digest"] = digest(changed["snapshot"])
        with pytest.raises(ValueError, match=match):
            RegistryEnvelope.model_validate(changed)


def test_differing_current_assertion_context_requires_a_source_backed_link() -> None:
    data = _envelope().model_dump(mode="json")
    other = _context("Former Synthetic Fund")
    data["snapshot"]["funds"][0]["current_proof"]["memberships"][0]["context"] = other
    data["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
        data["snapshot"]["funds"][0]
    )
    data["digest"] = digest(data["snapshot"])
    with pytest.raises(ValueError, match="exact link"):
        RegistryEnvelope.model_validate(data)
    proof = data["snapshot"]["funds"][0]["current_proof"]
    proof["current_context_links"] = [
        {
            "from_context": other,
            "to_context": _context(),
            "source_ids": ["member"],
        }
    ]
    data["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
        data["snapshot"]["funds"][0]
    )
    data["digest"] = digest(data["snapshot"])
    linked = RegistryEnvelope.model_validate(data)
    validate_publication(linked, None, expected_parent_digest=None, checked_at=CHECK)


def test_registry_requires_distinct_approving_audit_actors() -> None:
    for actor, field, value in (
        ("reviewer", "identity", "synthetic-curator"),
        ("reviewer", "review_disposition", "reject"),
        ("curator", "role", "reader"),
    ):
        data = _envelope().model_dump(mode="json")
        data["snapshot"]["audit"][actor][field] = value
        data["digest"] = digest(data["snapshot"])
        with pytest.raises(ValueError):
            RegistryEnvelope.model_validate(data)


def test_registry_strict_json_canonical_identifiers_and_bounds() -> None:
    from etf_advisor.domain.fund_identity import valid_key

    assert valid_key(KEY, REGISTRY_ID)
    assert not valid_key(KEY.upper(), REGISTRY_ID)
    assert not valid_key(KEY.replace("2222-4222", "2222-1222"), REGISTRY_ID)
    raw = _envelope().model_dump_json()
    with pytest.raises(ValueError):
        RegistryEnvelope.from_json(raw[:-1] + ',"digest":"' + "0" * 64 + '"}')
    data = _envelope().model_dump(mode="json")
    data["snapshot"]["sources"][0]["locator"] = "x" * 1001
    data["digest"] = digest(data["snapshot"])
    with pytest.raises(ValueError, match="text limit"):
        RegistryEnvelope.model_validate(data)
    data = _envelope().model_dump(mode="json")
    data["snapshot"]["sources"].reverse()
    data["digest"] = digest(data["snapshot"])
    with pytest.raises(ValueError, match="sorted"):
        RegistryEnvelope.model_validate(data)
    with pytest.raises(ValueError, match="check time must be UTC"):
        validate_publication(
            _envelope(),
            None,
            expected_parent_digest=None,
            checked_at=CHECK.replace(tzinfo=None),
        )


def _successor(parent: RegistryEnvelope, at: datetime, *, rename: bool) -> RegistryEnvelope:
    data = parent.model_dump(mode="json")
    snap = data["snapshot"]
    snap["generation"] = 2
    snap["parent_digest"] = parent.digest
    snap["recorded_at"] = _at(at)
    snap["sources"].extend(
        _source(name, at) for name in ("new_fund", "new_inventory", "new_member")
    )
    snap["sources"].sort(key=lambda item: item["id"])
    fund = snap["funds"][0]
    old_context = deepcopy(fund["context"])
    new_context = _context("Renamed Synthetic Fund") if rename else old_context
    fund["context"] = new_context
    fund["current_proof"] = {
        "fund": {"context": new_context, "source_ids": ["new_fund"]},
        "inventory": {"context": new_context, "source_ids": ["new_inventory"]},
        "memberships": [{"isin": CLASS, "context": new_context, "source_ids": ["new_member"]}],
        "current_context_links": [],
        "lineage_source_ids": ["fund"] if rename else [],
    }
    fund["members"][0]["source_ids"] = ["member", "new_member"]
    if rename:
        fund["aliases"] = [{"context": old_context, "source_ids": ["fund"]}]
    snap["audit"]["attested_at"] = _at(at)
    snap["audit"]["compared_parent_digest"] = parent.digest
    snap["audit"]["transitions"] = [
        {
            "key": KEY,
            "before_digest": digest(parent.snapshot.funds[0].model_dump(mode="json")),
            "after_digest": digest(fund),
            "operations": ["membership", "rename"] if rename else ["membership"],
            "source_ids": ["new_fund"],
        }
    ]
    old_row = {
        "key": KEY,
        "isin": CLASS,
        "source_locator": "synthetic#new_member",
        "before_status": "active",
        "after_status": None if rename else "active",
        "disposition": "changed" if rename else "unchanged",
        "source_ids": ["new_member"],
    }
    checks = [{"context": old_context, "source_ids": ["new_inventory"], "rows": [old_row]}]
    if rename:
        checks.append(
            {
                "context": new_context,
                "source_ids": ["new_inventory"],
                "rows": [
                    {
                        **old_row,
                        "before_status": None,
                        "after_status": "active",
                        "disposition": "added",
                    }
                ],
            }
        )
    snap["audit"]["inventory_checks"] = sorted(
        checks, key=lambda item: json.dumps(item["context"], sort_keys=True)
    )
    data["digest"] = digest(snap)
    return RegistryEnvelope.model_validate(data)


def test_historical_rename_lineage_does_not_expire_current_endpoint() -> None:
    parent = _envelope()
    later = CHECK + timedelta(days=730)
    successor = _successor(parent, later, rename=True)
    validate_publication(successor, parent, expected_parent_digest=parent.digest, checked_at=later)
    assert resolve_group(successor, KEY, CLASS, later) == later
    assert successor.snapshot.sources[0].observed_at == CHECK


def test_completed_rename_lineage_survives_third_generation_fresh_refresh() -> None:
    first = _envelope()
    second_at = CHECK + timedelta(days=730)
    second = _successor(first, second_at, rename=True)
    validate_publication(second, first, expected_parent_digest=first.digest, checked_at=second_at)

    third_at = second_at + timedelta(days=730)
    data = second.model_dump(mode="json")
    snapshot = data["snapshot"]
    snapshot["generation"] = 3
    snapshot["parent_digest"] = second.digest
    snapshot["recorded_at"] = _at(third_at)
    snapshot["sources"].extend(
        _source(source_id, third_at)
        for source_id in ("third_fund", "third_inventory", "third_member")
    )
    snapshot["sources"].sort(key=lambda source: source["id"])
    fund = snapshot["funds"][0]
    fund["current_proof"]["fund"]["source_ids"] = ["third_fund"]
    fund["current_proof"]["inventory"]["source_ids"] = ["third_inventory"]
    fund["current_proof"]["memberships"][0]["source_ids"] = ["third_member"]
    fund["members"][0]["source_ids"].append("third_member")
    fund["members"][0]["source_ids"].sort()
    snapshot["audit"]["attested_at"] = _at(third_at)
    snapshot["audit"]["compared_parent_digest"] = second.digest
    snapshot["audit"]["transitions"] = [
        {
            "key": KEY,
            "before_digest": digest(second.snapshot.funds[0].model_dump(mode="json")),
            "after_digest": digest(fund),
            "operations": ["membership"],
            "source_ids": ["third_fund"],
        }
    ]
    snapshot["audit"]["inventory_checks"] = [
        {
            "context": fund["context"],
            "source_ids": ["third_inventory"],
            "rows": [
                {
                    "key": KEY,
                    "isin": CLASS,
                    "source_locator": "synthetic#third_member",
                    "before_status": "active",
                    "after_status": "active",
                    "disposition": "unchanged",
                    "source_ids": ["third_member"],
                }
            ],
        }
    ]
    data["digest"] = digest(snapshot)
    third = RegistryEnvelope.model_validate(data)
    validate_publication(third, second, expected_parent_digest=second.digest, checked_at=third_at)
    assert resolve_group(third, KEY, CLASS, third_at) == third_at
    assert "fund" in third.snapshot.funds[0].current_proof.lineage_source_ids

    fund["current_proof"]["lineage_source_ids"] = []
    snapshot["audit"]["transitions"][0]["after_digest"] = digest(fund)
    data["digest"] = digest(snapshot)
    removed = RegistryEnvelope.model_validate(data)
    with pytest.raises(ValueError, match="historical lineage source deleted"):
        validate_publication(
            removed, second, expected_parent_digest=second.digest, checked_at=third_at
        )


def test_actual_parent_transition_and_inventory_are_required() -> None:
    parent = _envelope()
    later = CHECK + timedelta(hours=1)
    valid = _successor(parent, later, rename=False)
    validate_publication(valid, parent, expected_parent_digest=parent.digest, checked_at=later)
    for field, match in (
        ("transitions", "transition coverage"),
        ("inventory_checks", "inventory coverage"),
    ):
        data = valid.model_dump(mode="json")
        data["snapshot"]["audit"][field] = []
        data["digest"] = digest(data["snapshot"])
        with pytest.raises(ValueError, match=match):
            validate_publication(
                RegistryEnvelope.model_validate(data),
                parent,
                expected_parent_digest=parent.digest,
                checked_at=later,
            )
    data = valid.model_dump(mode="json")
    data["snapshot"]["audit"]["transitions"][0]["before_digest"] = "0" * 64
    data["digest"] = digest(data["snapshot"])
    with pytest.raises(ValueError, match="before digest"):
        validate_publication(
            RegistryEnvelope.model_validate(data),
            parent,
            expected_parent_digest=parent.digest,
            checked_at=later,
        )
    for change, match in (
        ({"disposition": "changed"}, "disposition"),
        ({"source_locator": "unbacked"}, "locator"),
    ):
        data = valid.model_dump(mode="json")
        data["snapshot"]["audit"]["inventory_checks"][0]["rows"][0].update(change)
        data["digest"] = digest(data["snapshot"])
        with pytest.raises(ValueError, match=match):
            validate_publication(
                RegistryEnvelope.model_validate(data),
                parent,
                expected_parent_digest=parent.digest,
                checked_at=later,
            )


def _unresolved_inventory_row(source_id: str) -> dict:
    return {
        "key": None,
        "isin": None,
        "source_locator": f"synthetic#{source_id}",
        "before_status": None,
        "after_status": None,
        "disposition": "unresolved",
        "source_ids": [source_id],
    }


def test_unmapped_inventory_suspends_initial_and_successor_active_contexts() -> None:
    initial = _envelope().model_dump(mode="json")
    initial["snapshot"]["audit"]["inventory_checks"][0]["rows"].insert(
        0, _unresolved_inventory_row("inventory")
    )
    initial["digest"] = digest(initial["snapshot"])
    with pytest.raises(ValueError, match="unresolved inventory"):
        RegistryEnvelope.model_validate(initial)
    false_resolution = deepcopy(initial)
    false_resolution["snapshot"]["audit"]["inventory_checks"][0]["rows"][0]["disposition"] = (
        "unchanged"
    )
    false_resolution["digest"] = digest(false_resolution["snapshot"])
    with pytest.raises(ValueError, match="unmapped inventory row must be unresolved"):
        RegistryEnvelope.model_validate(false_resolution)

    initial["snapshot"]["funds"][0]["status"] = "suspended"
    initial["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
        initial["snapshot"]["funds"][0]
    )
    initial["digest"] = digest(initial["snapshot"])
    suspended_initial = RegistryEnvelope.model_validate(initial)
    validate_publication(suspended_initial, None, expected_parent_digest=None, checked_at=CHECK)

    parent = _envelope()
    later = CHECK + timedelta(hours=1)
    resolved = _successor(parent, later, rename=False)
    validate_publication(resolved, parent, expected_parent_digest=parent.digest, checked_at=later)
    successor = resolved.model_dump(mode="json")
    successor["snapshot"]["audit"]["inventory_checks"][0]["rows"].insert(
        0, _unresolved_inventory_row("new_inventory")
    )
    successor["digest"] = digest(successor["snapshot"])
    with pytest.raises(ValueError, match="unresolved inventory"):
        RegistryEnvelope.model_validate(successor)

    successor["snapshot"]["funds"][0]["status"] = "suspended"
    successor["snapshot"]["audit"]["transitions"][0]["operations"] = [
        "membership",
        "suspend",
    ]
    successor["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
        successor["snapshot"]["funds"][0]
    )
    successor["digest"] = digest(successor["snapshot"])
    suspended_successor = RegistryEnvelope.model_validate(successor)
    validate_publication(
        suspended_successor,
        parent,
        expected_parent_digest=parent.digest,
        checked_at=later,
    )


def test_unmapped_inventory_in_alias_or_linked_context_blocks_active_fund() -> None:
    parent = _envelope()
    later = CHECK + timedelta(hours=1)
    old_context = parent.snapshot.funds[0].context.model_dump(mode="json")
    alias_data = _successor(parent, later, rename=True).model_dump(mode="json")
    alias_check = next(
        check
        for check in alias_data["snapshot"]["audit"]["inventory_checks"]
        if check["context"] == old_context
    )
    alias_check["rows"].insert(0, _unresolved_inventory_row("new_inventory"))
    alias_data["digest"] = digest(alias_data["snapshot"])
    with pytest.raises(ValueError, match="unresolved inventory"):
        RegistryEnvelope.model_validate(alias_data)

    data = _successor(parent, later, rename=True).model_dump(mode="json")
    fund = data["snapshot"]["funds"][0]
    fund["current_proof"]["inventory"]["context"] = old_context
    fund["current_proof"]["current_context_links"] = [
        {
            "from_context": old_context,
            "to_context": fund["context"],
            "source_ids": ["new_inventory"],
        }
    ]
    data["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(fund)
    data["digest"] = digest(data["snapshot"])
    linked = RegistryEnvelope.model_validate(data)
    validate_publication(linked, parent, expected_parent_digest=parent.digest, checked_at=later)

    old_check = next(
        check
        for check in data["snapshot"]["audit"]["inventory_checks"]
        if check["context"] == old_context
    )
    old_check["rows"].insert(0, _unresolved_inventory_row("new_inventory"))
    data["digest"] = digest(data["snapshot"])
    with pytest.raises(ValueError, match="unresolved inventory"):
        RegistryEnvelope.model_validate(data)


def test_future_current_constituent_boundary_and_historical_dual_role() -> None:
    at = CHECK + timedelta(minutes=5)
    assert resolve_group(_envelope(observation=at), KEY, CLASS, CHECK) == at
    parent = _envelope()
    later = CHECK + timedelta(days=730)
    successor = _successor(parent, later, rename=True)
    data = successor.model_dump(mode="json")
    data["snapshot"]["funds"][0]["current_proof"]["lineage_source_ids"] = ["fund", "new_fund"]
    data["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
        data["snapshot"]["funds"][0]
    )
    data["digest"] = digest(data["snapshot"])
    assert resolve_group(RegistryEnvelope.model_validate(data), KEY, CLASS, later) == later
    data["snapshot"]["funds"][0]["current_proof"]["fund"]["source_ids"] = ["fund", "new_fund"]
    data["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
        data["snapshot"]["funds"][0]
    )
    data["digest"] = digest(data["snapshot"])
    with pytest.raises(ValueError, match="stale or future"):
        resolve_group(RegistryEnvelope.model_validate(data), KEY, CLASS, later)


def test_retained_history_and_inactive_membership_cannot_be_silently_rewritten() -> None:
    parent = _envelope()
    later = CHECK + timedelta(hours=1)
    successor = _successor(parent, later, rename=False)
    for mutation, match in (
        (lambda data: data["snapshot"]["sources"].pop(0), "retained source"),
        (
            lambda data: data["snapshot"]["funds"][0]["members"][0].update(
                source_ids=["new_member"]
            ),
            "historical class source",
        ),
    ):
        data = successor.model_dump(mode="json")
        mutation(data)
        data["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
            data["snapshot"]["funds"][0]
        )
        data["digest"] = digest(data["snapshot"])
        with pytest.raises(ValueError, match=match):
            validate_publication(
                RegistryEnvelope.model_validate(data),
                parent,
                expected_parent_digest=parent.digest,
                checked_at=later,
            )
    inactive = successor.model_dump(mode="json")
    inactive["snapshot"]["funds"][0]["status"] = "suspended"
    inactive["snapshot"]["funds"][0]["members"][0]["status"] = "closed"
    inactive["snapshot"]["audit"]["inventory_checks"][0]["rows"][0]["after_status"] = "closed"
    inactive["snapshot"]["audit"]["inventory_checks"][0]["rows"][0]["disposition"] = "changed"
    inactive["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
        inactive["snapshot"]["funds"][0]
    )
    inactive["digest"] = digest(inactive["snapshot"])
    with pytest.raises(ValueError, match="not active"):
        resolve_group(RegistryEnvelope.model_validate(inactive), KEY, CLASS, later)


def test_registry_recording_orders_collection_attestation_and_actual_parent() -> None:
    equal_parent = _envelope()
    equal_child = _successor(equal_parent, CHECK, rename=False)
    validate_publication(
        equal_child,
        equal_parent,
        expected_parent_digest=equal_parent.digest,
        checked_at=CHECK,
    )
    for mutation in (
        lambda data: data["snapshot"]["sources"][0].update(
            collected_at=_at(CHECK + timedelta(seconds=1))
        ),
        lambda data: data["snapshot"]["audit"].update(
            attested_at=_at(CHECK + timedelta(seconds=1))
        ),
    ):
        data = _envelope().model_dump(mode="json")
        mutation(data)
        data["digest"] = digest(data["snapshot"])
        with pytest.raises(ValueError, match="recording precedes"):
            RegistryEnvelope.model_validate(data)
    parent_data = _envelope().model_dump(mode="json")
    parent_data["snapshot"]["recorded_at"] = _at(CHECK + timedelta(hours=2))
    parent_data["digest"] = digest(parent_data["snapshot"])
    parent = RegistryEnvelope.model_validate(parent_data)
    child_at = CHECK + timedelta(hours=1)
    child = _successor(parent, child_at, rename=False)
    with pytest.raises(ValueError, match="precedes actual parent"):
        validate_publication(
            child, parent, expected_parent_digest=parent.digest, checked_at=child_at
        )


def test_unsupported_suspended_reactivation_rejects_both_operation_labels() -> None:
    parent_data = _envelope().model_dump(mode="json")
    parent_data["snapshot"]["funds"][0]["status"] = "suspended"
    parent_data["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
        parent_data["snapshot"]["funds"][0]
    )
    parent_data["digest"] = digest(parent_data["snapshot"])
    parent = RegistryEnvelope.model_validate(parent_data)
    validate_publication(parent, None, expected_parent_digest=None, checked_at=CHECK)
    later = CHECK + timedelta(hours=1)
    successor = _successor(parent, later, rename=False)
    for operation in ("refresh", "suspend"):
        data = successor.model_dump(mode="json")
        data["snapshot"]["funds"][0]["status"] = "active"
        data["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(
            data["snapshot"]["funds"][0]
        )
        data["snapshot"]["audit"]["transitions"][0]["operations"] = [operation]
        data["digest"] = digest(data["snapshot"])
        with pytest.raises(ValueError, match="reactivation is not authorized"):
            validate_publication(
                RegistryEnvelope.model_validate(data),
                parent,
                expected_parent_digest=parent.digest,
                checked_at=later,
            )


def test_same_status_refresh_suspension_and_retirement_remain_supported() -> None:
    parent = _envelope()
    later = CHECK + timedelta(hours=1)
    baseline = _successor(parent, later, rename=False).model_dump(mode="json")
    for status, operations in (
        ("active", ["refresh"]),
        ("suspended", ["suspend"]),
        ("retired", ["retire"]),
    ):
        data = deepcopy(baseline)
        fund = data["snapshot"]["funds"][0]
        fund["status"] = status
        fund["members"][0]["source_ids"] = ["member"]
        data["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(fund)
        data["snapshot"]["audit"]["transitions"][0]["operations"] = operations
        data["digest"] = digest(data["snapshot"])
        validate_publication(
            RegistryEnvelope.model_validate(data),
            parent,
            expected_parent_digest=parent.digest,
            checked_at=later,
        )


def _three_fund_envelope() -> tuple[RegistryEnvelope, list[str]]:
    data = _envelope().model_dump(mode="json")
    snapshot = data["snapshot"]
    ids = ["US78462F1030", "IE00B5BMR087", "US9219378356"]
    keys = [new_key(REGISTRY_ID, str(UUID(int=UUID(FUND_ID).int + offset))) for offset in (0, 1, 2)]
    funds = []
    transitions = []
    checks = []
    for index, (isin, key) in enumerate(zip(ids, keys, strict=True)):
        fund = deepcopy(_fund())
        context = _context(f"Synthetic Fund {index}")
        fund["key"] = key
        fund["context"] = context
        fund["members"][0]["isin"] = isin
        for name in ("fund", "inventory"):
            fund["current_proof"][name]["context"] = context
        fund["current_proof"]["memberships"][0]["context"] = context
        fund["current_proof"]["memberships"][0]["isin"] = isin
        funds.append(fund)
        transitions.append(
            {
                "key": key,
                "before_digest": None,
                "after_digest": digest(fund),
                "operations": ["issue"],
                "source_ids": ["fund"],
            }
        )
        checks.append(
            {
                "context": context,
                "source_ids": ["inventory"],
                "rows": [
                    {
                        "key": key,
                        "isin": isin,
                        "source_locator": "synthetic#member",
                        "before_status": None,
                        "after_status": "active",
                        "disposition": "added",
                        "source_ids": ["member"],
                    }
                ],
            }
        )
    snapshot["funds"] = funds
    snapshot["audit"]["transitions"] = transitions
    snapshot["audit"]["inventory_checks"] = checks
    snapshot["audit"]["comparisons"] = [
        {"left_key": left, "right_key": right, "disposition": "distinct", "source_ids": ["fund"]}
        for left in keys
        for right in keys
        if left < right
    ]
    data["digest"] = digest(snapshot)
    return RegistryEnvelope.model_validate(data), keys


def test_same_fund_two_classes_and_distinct_same_umbrella_funds() -> None:
    one = _envelope().model_dump(mode="json")
    second_isin = "US78462F1030"
    fund = one["snapshot"]["funds"][0]
    fund["members"].append({"isin": second_isin, "status": "active", "source_ids": ["member"]})
    fund["members"].sort(key=lambda item: item["isin"])
    fund["current_proof"]["memberships"].append(
        {
            "isin": second_isin,
            "context": fund["context"],
            "source_ids": ["member"],
        }
    )
    fund["current_proof"]["memberships"].sort(key=lambda item: item["isin"])
    one["snapshot"]["audit"]["transitions"][0]["after_digest"] = digest(fund)
    one["snapshot"]["audit"]["inventory_checks"][0]["rows"].append(
        {
            "key": KEY,
            "isin": second_isin,
            "source_locator": "synthetic#member",
            "before_status": None,
            "after_status": "active",
            "disposition": "added",
            "source_ids": ["member"],
        }
    )
    one["snapshot"]["audit"]["inventory_checks"][0]["rows"].sort(
        key=lambda item: (item["key"], item["isin"], item["source_locator"])
    )
    one["digest"] = digest(one["snapshot"])
    envelope = RegistryEnvelope.model_validate(one)
    validate_publication(envelope, None, expected_parent_digest=None, checked_at=CHECK)
    assert resolve_group(envelope, KEY, CLASS, CHECK) == resolve_group(
        envelope, KEY, second_isin, CHECK
    )

    separate, keys = _three_fund_envelope()
    validate_publication(separate, None, expected_parent_digest=None, checked_at=CHECK)
    assert len(set(keys)) == 3
    assert len({fund.context.umbrella_legal_name for fund in separate.snapshot.funds}) == 1
    unresolved = separate.model_dump(mode="json")
    unresolved["snapshot"]["audit"]["comparisons"][0]["disposition"] = "unresolved"
    unresolved["digest"] = digest(unresolved["snapshot"])
    with pytest.raises(ValueError, match="unresolved same-Fund collision"):
        RegistryEnvelope.model_validate(unresolved)


def test_normalized_name_collision_still_requires_explicit_distinct_comparison() -> None:
    from etf_advisor.domain.fund_identity import _diagnostic

    envelope, _ = _three_fund_envelope()
    data = envelope.model_dump(mode="json")
    funds = data["snapshot"]["funds"]
    for index, name in ((0, "Synthetic-Fund"), (1, "SYNTHETIC FUND")):
        fund = funds[index]
        context = deepcopy(fund["context"])
        context["fund_legal_name"] = name
        context["jurisdiction"] = "IE" if index == 0 else "LU"
        fund["context"] = context
        for field in ("fund", "inventory"):
            fund["current_proof"][field]["context"] = context
        fund["current_proof"]["memberships"][0]["context"] = context
        data["snapshot"]["audit"]["transitions"][index]["after_digest"] = digest(fund)
        data["snapshot"]["audit"]["inventory_checks"][index]["context"] = context
    data["snapshot"]["audit"]["inventory_checks"].sort(
        key=lambda item: json.dumps(item["context"], sort_keys=True)
    )
    data["digest"] = digest(data["snapshot"])
    distinct = RegistryEnvelope.model_validate(data)
    assert _diagnostic(distinct.snapshot.funds[0].context) == _diagnostic(
        distinct.snapshot.funds[1].context
    )
    validate_publication(distinct, None, expected_parent_digest=None, checked_at=CHECK)
    data["snapshot"]["audit"]["comparisons"] = data["snapshot"]["audit"]["comparisons"][1:]
    data["digest"] = digest(data["snapshot"])
    with pytest.raises(ValueError, match="issuance omitted"):
        validate_publication(
            RegistryEnvelope.model_validate(data),
            None,
            expected_parent_digest=None,
            checked_at=CHECK,
        )


def _curator_pipeline():
    from test_us_eu_contract import _fx, _profile, _record

    from etf_advisor.domain.construction import (
        PortfolioConstructionInput,
        construct_model_portfolio,
    )
    from etf_advisor.domain.policy import calculate_policy
    from etf_advisor.domain.screening import screen_candidate_evidence
    from etf_advisor.rag.evidence import CandidateEvidenceBundle, select_candidate_evidence
    from etf_advisor.rag.models import GraphEnrichedSource
    from etf_advisor.research.models import ETFResearchSnapshot

    envelope, keys = _three_fund_envelope()
    validate_publication(envelope, None, expected_parent_digest=None, checked_at=CHECK)
    listings = [
        ("SPY", "NYQ", "USD", "Large Blend", "US78462F1030"),
        ("CSPX.AS", "AMS", "EUR", "Large Growth", "IE00B5BMR087"),
        ("BND", "NYQ", "USD", "Intermediate Core Bond", "US9219378356"),
    ]
    records = []
    for listing, key in zip(listings, keys, strict=True):
        record = _record(*listing)
        for field in record.research_fields().values():
            field.observed_at = CHECK
            field.ingested_at = CHECK
        record.economic_group_id.value = key
        record.economic_group_id.unit = "curator_fund_id"
        record.economic_group_id.provider = "audited_curator_registry_v1"
        record.economic_group_id.source_url = "https://example.invalid/fund"
        record = record.model_copy(
            update={
                "identity_contract": "curator-fund-v1",
                "registry_envelope": envelope,
            }
        )
        records.append(type(record).model_validate(record.model_dump(mode="json")))
    snapshot = ETFResearchSnapshot(
        schema_version=2,
        advisory_contract="us-eu-v1",
        identity_contract="curator-fund-v1",
        registry_envelope=envelope,
        snapshot_version="synthetic-1",
        universe_id="synthetic",
        universe_version="1",
        ingested_at=CHECK,
        records=records,
    )
    saved = ETFResearchSnapshot.model_validate_json(snapshot.model_dump_json())
    assert saved.content_digest() == snapshot.content_digest()
    profile = _profile().model_copy(update={"identity_contract": "curator-fund-v1"})
    profile = type(profile).model_validate(profile.model_dump(mode="json"))
    sources = [
        GraphEnrichedSource(
            document_id=doc.document_id,
            content=doc.content,
            metadata=doc.metadata,
            distance=0.1,
        )
        for doc in saved.to_source_documents()
    ]
    evidence = select_candidate_evidence(
        profile,
        sources,
        query="synthetic",
        checked_at=CHECK,
        max_age=timedelta(hours=120),
        limit=3,
        fx_reference=_fx(observed_at=CHECK, effective_date=CHECK.date()),
    )
    assert evidence.status == "ready"
    assert CandidateEvidenceBundle.model_validate_json(evidence.model_dump_json()) == evidence
    screening = screen_candidate_evidence(evidence)
    construction = construct_model_portfolio(
        PortfolioConstructionInput(
            profile=profile,
            policy_calculation=calculate_policy(profile),
            candidate_evidence=evidence,
            candidate_screening=screening,
        )
    )
    assert construction.status == "ready"
    assert {position.identity_contract for position in construction.draft.positions} == {
        "curator-fund-v1"
    }
    return snapshot, profile, evidence, screening, construction


def test_curator_identity_flows_through_saved_research_evidence_and_construction() -> None:
    _curator_pipeline()


def test_bound_replay_rejects_marker_downgrade_and_never_reads_live_registry(monkeypatch) -> None:
    from etf_advisor.rag.evidence import CandidateEvidenceBundle
    from etf_advisor.research.models import ETFResearchSnapshot

    snapshot, _, evidence, screening, construction = _curator_pipeline()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("saved replay must not read active registry")

    monkeypatch.setattr(LocalFundIdentityRegistry, "active", forbidden)
    assert ETFResearchSnapshot.model_validate_json(snapshot.model_dump_json()) == snapshot
    assert CandidateEvidenceBundle.model_validate_json(evidence.model_dump_json()) == evidence
    assert type(screening).model_validate_json(screening.model_dump_json()) == screening
    assert type(construction).model_validate_json(construction.model_dump_json()) == construction
    stripped = snapshot.model_dump(mode="json")
    stripped.pop("identity_contract")
    stripped.pop("registry_envelope")
    for record in stripped["records"]:
        record.pop("identity_contract")
        record.pop("registry_envelope")
    with pytest.raises(ValueError):
        ETFResearchSnapshot.model_validate(stripped)
    for artifact in (evidence, screening, construction):
        data = artifact.model_dump(mode="json")
        data["identity_contract"] = None
        with pytest.raises(ValueError):
            type(artifact).model_validate(data)


def test_curator_explanation_and_review_retain_identity_contract() -> None:
    from etf_advisor.dashboard import ReviewPayload
    from etf_advisor.domain.policy import calculate_policy
    from etf_advisor.explanation.models import (
        ExplanationResult,
        GeneratedExplanation,
        GroundedStatement,
        build_explanation_request,
        validate_and_bundle_explanation,
    )

    _, profile, evidence, screening, construction = _curator_pipeline()
    policy = calculate_policy(profile)
    request = build_explanation_request(
        profile=profile.model_dump(mode="json"),
        draft_policy=policy.model_dump(mode="json"),
        candidate_evidence=evidence.model_dump(mode="json"),
        candidate_screening=screening.model_dump(mode="json"),
        portfolio_construction=construction.model_dump(mode="json"),
    )
    assert request.identity_contract == "curator-fund-v1"
    generated = GeneratedExplanation(
        summary=GroundedStatement(
            text="This illustrative draft follows the policy.",
            basis="policy_calculation",
            references=["policy.notes"],
        ),
        policy_points=[
            GroundedStatement(
                text="The base currency is USD.",
                basis="policy_calculation",
                references=["policy.base_currency"],
            )
        ],
        evidence_points=[
            GroundedStatement(
                text="SPY has selected source evidence.",
                basis="source_evidence",
                references=[evidence.candidates[0].document_id],
                subject_symbols=["SPY"],
            )
        ],
        tradeoffs=[
            GroundedStatement(
                text="The illustrative rules require review.",
                basis="policy_calculation",
                references=["policy.notes"],
            )
        ],
    )
    explanation = validate_and_bundle_explanation(
        request,
        ExplanationResult(provider="synthetic", model="offline", explanation=generated),
    )
    assert explanation.identity_contract == "curator-fund-v1"
    review = ReviewPayload(
        kind="portfolio_policy_review",
        question="Review synthetic draft?",
        allowed_actions=["approve", "edit", "reject"],
        draft_policy=policy,
        candidate_evidence=evidence,
        candidate_screening=screening,
        portfolio_construction=construction,
        draft_explanation=explanation,
    )
    assert ReviewPayload.model_validate_json(review.model_dump_json()) == review
    downgraded = review.model_dump(mode="json")
    downgraded["draft_explanation"].pop("identity_contract")
    with pytest.raises(ValueError):
        ReviewPayload.model_validate(downgraded)


def test_saved_revision_rejects_identity_contract_switch() -> None:
    from etf_advisor.domain.construction import PortfolioConstructionPolicy
    from etf_advisor.domain.revision import ReviewDecision, RevisionInputs, plan_revision
    from etf_advisor.domain.screening import CandidateScreeningPolicy

    _, profile, _, _, _ = _curator_pipeline()
    inputs = RevisionInputs(
        profile=profile,
        screening_policy=CandidateScreeningPolicy(),
        construction_policy=PortfolioConstructionPolicy(),
        candidate_limit=3,
        with_evidence=True,
        with_explanation=False,
        explanation_instruction="",
    ).model_dump(mode="json")
    decision = ReviewDecision(
        decision_id="synthetic",
        revision_id="synthetic",
        action="edit",
        disposition="revise",
        note="Synthetic edit",
        submitted_at=CHECK,
        feedback=[{"kind": "profile", "patch": {"identity_contract": None}}],
    )
    with pytest.raises(ValueError, match="identity contracts"):
        plan_revision(decision, inputs)


def test_curator_graph_review_restore_and_downstream_revision_are_offline(monkeypatch) -> None:
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from test_workflow import review_decision as make_decision

    from etf_advisor.dashboard import review_payload
    from etf_advisor.graph.revision import validate_revision_state
    from etf_advisor.graph.workflow import build_graph

    _, profile, evidence, _, _ = _curator_pipeline()

    class Retriever:
        calls = 0

        def retrieve(self, _profile, *, limit):
            self.calls += 1
            copy = type(evidence).model_validate(evidence.model_dump(mode="json"))
            copy.requested_limit = limit
            return copy

    retriever = Retriever()
    saver = InMemorySaver()
    config = {"configurable": {"thread_id": "curator-synthetic"}, "recursion_limit": 100}
    graph = build_graph(checkpointer=saver, candidate_retriever=retriever, clock=lambda: CHECK)
    state = graph.invoke({"profile": profile.model_dump(mode="json")}, config)
    assert state["status"] == "awaiting_human_review", state.get("errors")
    assert validate_revision_state(state).revisions[0].receipts[0].status == "succeeded"

    def forbidden(*_args, **_kwargs):
        raise AssertionError("offline restore cannot consult active registry or clock")

    monkeypatch.setattr(LocalFundIdentityRegistry, "active", forbidden)
    restored = build_graph(checkpointer=saver, clock=forbidden)
    retained = dict(restored.get_state(config).values)
    retained["__interrupt__"] = restored.get_state(config).interrupts
    assert review_payload(retained)["candidate_evidence"]["identity_contract"] == "curator-fund-v1"
    assert retriever.calls == 1
    state = graph.invoke(
        Command(
            resume={
                **make_decision(
                    state,
                    "edit",
                    [
                        {
                            "kind": "construction_policy",
                            "patch": {"max_positions": 4},
                        }
                    ],
                ),
                "submitted_at": _at(CHECK),
            }
        ),
        config,
    )
    assert state["status"] == "awaiting_human_review", state.get("errors")
    assert retriever.calls == 1
    assert state["candidate_evidence"]["identity_contract"] == "curator-fund-v1"


def test_reference_schema2_requires_matching_bound_provider_class_and_url(tmp_path) -> None:
    from test_us_eu_contract import _reference_record

    from etf_advisor.data.reference_facts import ReferenceFactsFile, load_reference_facts

    envelope, keys = _three_fund_envelope()
    record = _reference_record()
    for name in (
        "share_class_id",
        "economic_group_id",
        "domicile",
        "fund_base_currency",
        "share_class_currency",
    ):
        field = getattr(record, name)
        field.observed_at = CHECK
        field.ingested_at = CHECK
    record.economic_group_id.value = envelope.snapshot.funds[0].key
    record.economic_group_id.unit = "curator_fund_id"
    record.economic_group_id.provider = "audited_curator_registry_v1"
    record.economic_group_id.source_url = "https://example.invalid/fund"
    file = ReferenceFactsFile.model_validate(
        {
            "schema_version": 2,
            "identity_contract": "curator-fund-v1",
            "registry_envelope": envelope.model_dump(mode="json"),
            "records": [record.model_dump(mode="json")],
        }
    )
    path = tmp_path / "synthetic-reference.json"
    path.write_text(file.model_dump_json(), encoding="utf-8")
    loaded = load_reference_facts(path, ["SPY"])
    assert loaded.identity_contract == "curator-fund-v1"
    assert loaded.registry_envelope == envelope
    for change in (
        {"provider": "issuer"},
        {"source_url": "https://example.invalid/other"},
        {"value": keys[1]},
    ):
        data = file.model_dump(mode="json")
        data["records"][0]["economic_group_id"].update(change)
        with pytest.raises(ValueError):
            ReferenceFactsFile.model_validate(data)
    downgraded = file.model_dump(mode="json")
    downgraded["schema_version"] = 1
    downgraded.pop("identity_contract")
    downgraded.pop("registry_envelope")
    downgraded["records"][0]["economic_group_id"]["unit"] = "issuer_fund_id"
    with pytest.raises(ValueError):
        ReferenceFactsFile.model_validate(downgraded)


def test_curator_catalogue_job_cache_and_finalization_bind_reference(tmp_path) -> None:
    from test_issue105_catalogue import catalogue
    from test_us_eu_contract import _record, _reference_record

    from etf_advisor.catalogue.research_job import (
        ResearchJobPolicy,
        ResearchJobStore,
        advance_catalogue_research,
        begin_catalogue_research,
        finalize_catalogue_research,
    )
    from etf_advisor.catalogue.research_scope import plan_catalogue_scope
    from etf_advisor.data.reference_facts import ReferenceFactsFile

    envelope, keys = _three_fund_envelope()
    chosen = next(row["listing_id"] for row in catalogue()["direct"] if row["symbol"] == "U119")
    scope = plan_catalogue_scope(catalogue(), {"listing_ids": [chosen]})
    member = scope.members[0]
    reference = _reference_record()
    reference.symbol, reference.exchange = member.symbol, member.exchange
    reference.economic_group_id.value = keys[0]
    reference.economic_group_id.unit = "curator_fund_id"
    reference.economic_group_id.provider = "audited_curator_registry_v1"
    reference.economic_group_id.source_url = "https://example.invalid/fund"
    for field in (
        reference.share_class_id,
        reference.economic_group_id,
        reference.domicile,
        reference.fund_base_currency,
        reference.share_class_currency,
    ):
        field.observed_at = CHECK
        field.ingested_at = CHECK
    path = tmp_path / "references.json"
    path.write_text(
        ReferenceFactsFile.model_validate(
            {
                "schema_version": 2,
                "identity_contract": "curator-fund-v1",
                "registry_envelope": envelope.model_dump(mode="json"),
                "records": [reference.model_dump(mode="json")],
            }
        ).model_dump_json(),
        encoding="utf-8",
    )
    store = ResearchJobStore(tmp_path / "jobs")
    job = begin_catalogue_research(
        scope,
        [path],
        ResearchJobPolicy(),
        clock=lambda: CHECK,
        store=store,
    )

    class SyntheticCollector:
        def collect(self, listing, snapshot_version, references, budget, *, clock):
            record = _record(listing.symbol, listing.exchange, "USD", "Large Blend", "US78462F1030")
            for field in record.research_fields().values():
                field.observed_at = CHECK
                field.ingested_at = CHECK
                field.snapshot_version = snapshot_version
            for name in (
                "share_class_id",
                "economic_group_id",
                "domicile",
                "fund_base_currency",
                "share_class_currency",
            ):
                setattr(
                    record, name, getattr(references.lookup(listing.symbol, listing.exchange), name)
                )
                getattr(record, name).snapshot_version = snapshot_version
            return type(record).model_validate(
                record.model_copy(
                    update={
                        "identity_contract": "curator-fund-v1",
                        "registry_envelope": envelope,
                    }
                ).model_dump(mode="json")
            )

    job = advance_catalogue_research(
        job.job_id,
        job.generation,
        collector=SyntheticCollector(),
        store=store,
        clock=lambda: CHECK,
    )
    assert len(store.read(job.job_id).cached) == 1
    snapshot = finalize_catalogue_research(job.job_id, store=store, clock=lambda: CHECK)
    assert snapshot.identity_contract == "curator-fund-v1"
    assert snapshot.registry_envelope == envelope
    assert store.read(job.job_id).finalization is not None
    tampered = store.read(job.job_id).model_dump(mode="json")
    tampered["references"][0]["economic_group_id"]["value"] = keys[1]
    tampered["reference_digest"] = digest(tampered["references"])
    store._path(job.job_id).write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="collected_curator_reference_substitution"):
        store.read(job.job_id)
