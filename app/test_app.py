import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def make_event(client, title="Team dinner"):
    return client.post(
        "/events/new",
        data={"title": title, "event_date": "2026-12-20T19:00", "location": "Cafe"},
    )


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_create_event_and_list(client):
    resp = make_event(client)
    assert resp.status_code == 302
    assert b"Team dinner" in client.get("/").data


def test_create_event_requires_title(client):
    resp = client.post("/events/new", data={"title": "", "event_date": ""})
    assert resp.status_code == 400


def test_rsvp_and_update(client):
    make_event(client)
    client.post("/events/1/rsvp", data={"name": "Asha", "status": "yes"})
    client.post("/events/1/rsvp", data={"name": "Ravi", "status": "maybe"})
    client.post("/events/1/rsvp", data={"name": "Asha", "status": "no"})  # changes her answer
    page = client.get("/").data.decode()
    assert "0 going" in page and "1 maybe" in page and "1 can't" in page


def test_invalid_status_rejected(client):
    make_event(client)
    client.post("/events/1/rsvp", data={"name": "X", "status": "definitely"})
    assert "0 going" in client.get("/").data.decode()


def test_delete_event(client):
    make_event(client)
    client.post("/events/1/rsvp", data={"name": "Asha", "status": "yes"})
    client.post("/events/1/delete")
    assert client.get("/events/1").status_code == 404
