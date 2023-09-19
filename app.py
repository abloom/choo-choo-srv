import datetime
import json
import os
from pprint import pprint
import requests
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ROUTES_AND_STOPS_TO_TRACK = {
    "UP-NW": ["JEFFERSONP", "IRVINGPK"],
    "UP-W": ["OTC"],
    # "BNSF": [],
}

METRA_USER = os.getenv("METRA_USER")
METRA_PASS = os.getenv("METRA_PASS")

class MetraClient:
    base_headers = {'Accept': 'application/json'}

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    @property
    def base_url(self) -> str:
        return f"https://{self.username}:{self.password}@gtfsapi.metrarail.com/gtfs"

    def _get(self, url, headers = {}):
        url = self.base_url + url
        return requests.get(url, headers | self.base_headers).json()

    def trip_updates(self) -> dict:
        return self._get("/tripUpdates")

    def trips(self) -> dict:
        return self._get("/schedule/trips")

    def stops(self) -> dict:
        return self._get("/schedule/stops")

    def routes(self) -> dict:
        return self._get("/schedule/routes")

@app.template_filter()
def to_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys = True, indent = 4, separators = (',', ': '))

@app.template_filter()
def from_iso_to_datetime(iso_date: str) -> datetime:
    return datetime.datetime.fromisoformat(iso_date)

@app.template_filter()
def to_local_time(time: datetime) -> str:
    return time.astimezone().strftime("%-I:%M %p")

@app.route("/metra")
def metra():
    client = MetraClient(METRA_USER, METRA_PASS)

    # TODO cache this
    stops = {}
    for stop in client.stops():
        stops[stop["stop_id"]] = stop

    # TODO cache this
    routes = {}
    for route in client.routes():
        routes[route["route_id"]] = route

    # TODO maybe cache this
    trips = {}
    route_ids = ROUTES_AND_STOPS_TO_TRACK.keys()
    for trip in client.trips():
        if not route_ids or (trip["route_id"] in route_ids):
            # if not DIRECTION_ID or trip["direction_id"] == DIRECTION_ID:
            trips[trip["trip_id"]] = trip
    trip_ids = trips.keys()

    trip_updates = []
    for update in client.trip_updates():
        if update["is_deleted"]:
            next

        trip_update = update["trip_update"]
        trip = trip_update["trip"]
        if trip["trip_id"] in trip_ids:
            stop_time_updates = []
            stop_ids = ROUTES_AND_STOPS_TO_TRACK[trip["route_id"]]
            for stop_time in trip_update["stop_time_update"]:
                if not stop_ids or stop_time["stop_id"] in stop_ids:
                    stop_time_updates.append(stop_time)
            trip_update["stop_time_update"] = stop_time_updates

            if trip_update["stop_time_update"]:
                trip_updates.append(update)

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
