"""Event RSVP - a small dynamic Flask app backed by SQLite."""
import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for

STATUSES = ("yes", "maybe", "no")

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT,
    event_date  TEXT NOT NULL,
    location    TEXT,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rsvps (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('yes', 'maybe', 'no')),
    created_at TEXT NOT NULL,
    UNIQUE (event_id, name)
);
"""


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-secret")
    app.config["DATABASE"] = db_path or os.environ.get("DATABASE", "/data/rsvp.db")
    app.config["APP_VERSION"] = os.environ.get("APP_VERSION", "local")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        os.makedirs(os.path.dirname(os.path.abspath(app.config["DATABASE"])), exist_ok=True)
        get_db().executescript(SCHEMA)

    @app.context_processor
    def inject_version():
        return {"app_version": app.config["APP_VERSION"]}

    @app.route("/")
    def index():
        events = get_db().execute(
            """
            SELECT e.*,
                   SUM(CASE WHEN r.status = 'yes'   THEN 1 ELSE 0 END) AS yes_count,
                   SUM(CASE WHEN r.status = 'maybe' THEN 1 ELSE 0 END) AS maybe_count,
                   SUM(CASE WHEN r.status = 'no'    THEN 1 ELSE 0 END) AS no_count
            FROM events e LEFT JOIN rsvps r ON r.event_id = e.id
            GROUP BY e.id
            ORDER BY e.event_date ASC
            """
        ).fetchall()
        return render_template("index.html", events=events)

    @app.route("/events/new", methods=["GET", "POST"])
    def new_event():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            event_date = request.form.get("event_date", "").strip()
            if not title or not event_date:
                flash("Title and date are required.", "error")
                return render_template("new_event.html", form=request.form), 400
            db = get_db()
            cur = db.execute(
                "INSERT INTO events (title, description, event_date, location, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    title,
                    request.form.get("description", "").strip(),
                    event_date,
                    request.form.get("location", "").strip(),
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
            db.commit()
            flash("Event created. Share this page so people can RSVP.", "success")
            return redirect(url_for("event_detail", event_id=cur.lastrowid))
        return render_template("new_event.html", form={})

    def load_event(event_id):
        event = get_db().execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if event is None:
            abort(404)
        return event

    @app.route("/events/<int:event_id>")
    def event_detail(event_id):
        event = load_event(event_id)
        rsvps = get_db().execute(
            "SELECT * FROM rsvps WHERE event_id = ? ORDER BY created_at", (event_id,)
        ).fetchall()
        grouped = {s: [r for r in rsvps if r["status"] == s] for s in STATUSES}
        return render_template("event.html", event=event, grouped=grouped, statuses=STATUSES)

    @app.route("/events/<int:event_id>/rsvp", methods=["POST"])
    def rsvp(event_id):
        load_event(event_id)
        name = request.form.get("name", "").strip()
        status = request.form.get("status", "")
        if not name or status not in STATUSES:
            flash("Enter your name and pick Yes, Maybe or No.", "error")
            return redirect(url_for("event_detail", event_id=event_id))
        db = get_db()
        # One RSVP per name per event: answering again updates the earlier answer.
        db.execute(
            "INSERT INTO rsvps (event_id, name, status, created_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (event_id, name) DO UPDATE SET status = excluded.status",
            (event_id, name, status, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        db.commit()
        flash(f"Thanks {name}, your RSVP is saved as '{status}'.", "success")
        return redirect(url_for("event_detail", event_id=event_id))

    @app.route("/events/<int:event_id>/rsvps/<int:rsvp_id>/delete", methods=["POST"])
    def delete_rsvp(event_id, rsvp_id):
        db = get_db()
        db.execute("DELETE FROM rsvps WHERE id = ? AND event_id = ?", (rsvp_id, event_id))
        db.commit()
        return redirect(url_for("event_detail", event_id=event_id))

    @app.route("/events/<int:event_id>/delete", methods=["POST"])
    def delete_event(event_id):
        load_event(event_id)
        db = get_db()
        db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        db.commit()
        flash("Event deleted.", "success")
        return redirect(url_for("index"))

    @app.route("/health")
    def health():
        get_db().execute("SELECT 1")
        return {"status": "ok", "version": app.config["APP_VERSION"]}

    return app


if __name__ == "__main__":
    create_app(os.environ.get("DATABASE", "rsvp.db")).run(debug=True)
