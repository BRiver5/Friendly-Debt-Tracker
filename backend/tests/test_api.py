"""End-to-end API tests covering the full ledger flow."""
from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_device_register_is_idempotent(client):
    body = {"device_uuid": "device-1234-5678-9012"}
    r1 = client.post("/device/register", json=body)
    r2 = client.post("/device/register", json=body)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["uuid"] == r2.json()["uuid"]


def test_requires_device_header(client):
    r = client.get("/friends")
    assert r.status_code == 401


def test_friend_crud(client, headers):
    r = client.post("/friends", json={"name": "  Alex  ", "avatar_emoji": "🦊"},
                    headers=headers)
    assert r.status_code == 201
    friend = r.json()
    assert friend["name"] == "Alex"  # trimmed
    assert friend["balance"] == "0.00"
    assert friend["open_entry_count"] == 0

    fid = friend["id"]
    r = client.get("/friends", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.patch(f"/friends/{fid}", json={"name": "Alexandra"},
                     headers=headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Alexandra"


def test_balance_computation(client, headers):
    fid = client.post("/friends", json={"name": "Sam"}, headers=headers).json()["id"]

    # They owe me 50.00
    client.post("/entries", json={
        "friend_id": fid, "amount": "50.00", "direction": "THEY_OWE_ME",
        "description": "Concert tickets",
    }, headers=headers)
    # I owe them 20.50
    client.post("/entries", json={
        "friend_id": fid, "amount": "20.50", "direction": "I_OWE_THEM",
    }, headers=headers)

    detail = client.get(f"/friends/{fid}", headers=headers).json()
    assert detail["balance"] == "29.50"
    assert detail["open_entry_count"] == 2
    assert len(detail["entries"]) == 2

    summary = client.get("/stats/summary", headers=headers).json()
    assert summary["total_owed_to_me"] == "50.00"
    assert summary["total_i_owe"] == "20.50"
    assert summary["net_balance"] == "29.50"


def test_settle_up_zeroes_balance(client, headers):
    fid = client.post("/friends", json={"name": "Jo"}, headers=headers).json()["id"]
    client.post("/entries", json={
        "friend_id": fid, "amount": "15.00", "direction": "THEY_OWE_ME",
    }, headers=headers)

    r = client.post(f"/friends/{fid}/settle", headers=headers)
    assert r.status_code == 200
    assert r.json()["balance"] == "0.00"
    assert r.json()["open_entry_count"] == 0
    # Entry still exists, just settled.
    assert r.json()["entries"][0]["is_settled"] is True
    assert r.json()["entries"][0]["settled_at"] is not None


def test_entry_edit_and_settle_toggle(client, headers):
    fid = client.post("/friends", json={"name": "Kai"}, headers=headers).json()["id"]
    eid = client.post("/entries", json={
        "friend_id": fid, "amount": "10.00", "direction": "THEY_OWE_ME",
    }, headers=headers).json()["id"]

    r = client.patch(f"/entries/{eid}", json={"amount": "12.00",
                     "is_settled": True}, headers=headers)
    assert r.json()["amount"] == "12.00"
    assert r.json()["is_settled"] is True

    # Un-settle clears settled_at.
    r = client.patch(f"/entries/{eid}", json={"is_settled": False}, headers=headers)
    assert r.json()["is_settled"] is False
    assert r.json()["settled_at"] is None


def test_delete_entry_and_friend(client, headers):
    fid = client.post("/friends", json={"name": "Lee"}, headers=headers).json()["id"]
    eid = client.post("/entries", json={
        "friend_id": fid, "amount": "5.00", "direction": "I_OWE_THEM",
    }, headers=headers).json()["id"]

    assert client.delete(f"/entries/{eid}", headers=headers).status_code == 204
    assert client.get(f"/entries/{eid}", headers=headers).status_code == 404

    assert client.delete(f"/friends/{fid}", headers=headers).status_code == 204
    assert client.get(f"/friends/{fid}", headers=headers).status_code == 404


def test_data_is_scoped_per_device(client):
    a = {"X-Device-UUID": "device-aaaa-1111-2222-3333"}
    b = {"X-Device-UUID": "device-bbbb-4444-5555-6666"}
    client.post("/friends", json={"name": "Private"}, headers=a)

    assert len(client.get("/friends", headers=a).json()) == 1
    assert len(client.get("/friends", headers=b).json()) == 0


def test_entry_rejects_foreign_friend(client, headers):
    other = {"X-Device-UUID": "device-other-9999-8888-7777"}
    fid = client.post("/friends", json={"name": "Mine"}, headers=headers).json()["id"]
    # Device B cannot attach an entry to Device A's friend.
    r = client.post("/entries", json={
        "friend_id": fid, "amount": "1.00", "direction": "THEY_OWE_ME",
    }, headers=other)
    assert r.status_code == 404


def test_timeline_shape(client, headers):
    fid = client.post("/friends", json={"name": "Nas"}, headers=headers).json()["id"]
    client.post("/entries", json={
        "friend_id": fid, "amount": "40.00", "direction": "THEY_OWE_ME",
        "date": "2026-07-10",
    }, headers=headers)

    r = client.get("/stats/timeline?days=30", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["points"]) == 30
    assert data["points"][-1]["net_balance"] == "40.00"
    assert len(data["per_friend"]) == 1


def test_amount_must_be_positive(client, headers):
    fid = client.post("/friends", json={"name": "Ola"}, headers=headers).json()["id"]
    r = client.post("/entries", json={
        "friend_id": fid, "amount": "-5.00", "direction": "THEY_OWE_ME",
    }, headers=headers)
    assert r.status_code == 422
