import datetime
import json
import os
from dateutil.parser import isoparse
from flask import Flask, render_template
from dotenv import load_dotenv

from cache import cache
from metra import MetraClient

load_dotenv()

config = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "METRA_USER": os.getenv("METRA_USER"),
    "METRA_PASS": os.getenv("METRA_PASS"),
}

app = Flask(__name__)
app.config.from_mapping(config)
cache.init_app(app)

@app.template_filter()
def to_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys = True, indent = 4, separators = (',', ': '))

@app.template_filter()
def from_iso_to_datetime(iso_date: str) -> datetime:
    return isoparse(iso_date)

@app.template_filter()
def to_local_time(time: datetime) -> str:
    return time.astimezone().strftime("%-I:%M %p")

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

@app.route("/metra")
def metra():
    client = MetraClient(app.config["METRA_USER"], app.config["METRA_PASS"])
    stops = client.stops()
    routes = client.routes()
    trips = client.trips()

    trip_ids = trips.keys()
    trip_updates = client.trip_updates(trip_ids)
    trip_updates.reverse()

    return render_template("metra.html",
        trip_updates=trip_updates,
        stops=stops,
        routes=routes,
        trips=trips,
        directions={
            0: "Outbound",
            1: "Inbound",
        }
    )
