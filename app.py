from collections import defaultdict
from datetime import datetime, time
from functools import cached_property
import json
import os
from dateutil.parser import isoparse
from flask import Flask, render_template
from dotenv import load_dotenv

from cache import cache
from metra import MetraClient

load_dotenv()

ROUTES_AND_STOPS_TO_TRACK = {
    # "UP-NW": [],
    "UP-NW": ["JEFFERSONP"],
    "MD-N": ["FORESTGLEN"],
    # "UP-W": ["OTC"],
    # "BNSF": [],
}

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
    return json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': '), default=lambda o: o.__dict__)

@app.template_filter()
def from_iso_to_time(iso_time: str) -> datetime:
    try:
        return time.fromisoformat(iso_time)
    except ValueError:
        # some trips that end up running past midnight have an arrival time larger than 23 hours
        time_parts = iso_time.split(":")
        time_parts[0] = str(int(time_parts[0]) - 24).zfill(2)
        return time.fromisoformat(":".join(time_parts))

@app.template_filter()
def from_iso_to_datetime(iso_date: str) -> datetime:
    return isoparse(iso_date)

@app.template_filter()
def to_local_time(time: datetime) -> str:
    return time.strftime("%-I:%M %p")

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

class MetraStop:
    def __init__(self, route, stop) -> None:
        self.stop_sequence = None
        self.route = route
        self.stop = stop
        self._times = {
            0: [],
            1: [],
        }

    @cached_property
    def times(self) -> dict:
        filtered_times = {
            0: [],
            1: [],
        }

        now = datetime.now().time()
        for direction, stop_times in self._times.items():
            for stop_time in stop_times:
                arrival_time = from_iso_to_time(stop_time["arrival_time"])
                if now <= arrival_time:
                    filtered_times[direction].append(stop_time)

        return filtered_times


    def add_time(self, direction_id, stop_time) -> None:
        if stop_time["stop_id"] == self.stop["stop_id"]:
            if direction_id == 0:
                self.stop_sequence = stop_time["stop_sequence"]
            self._times[direction_id].append(stop_time)

    def sort_times(self) -> None:
        for direction_id, stop_times in self.times.items():
            self._times[direction_id] = sorted(stop_times, key=lambda x: x["arrival_time"])

@app.route("/metra")
def metra():
    client = MetraClient(app.config["METRA_USER"], app.config["METRA_PASS"], ROUTES_AND_STOPS_TO_TRACK)

    routes = client.routes()
    calendars = client.calendars()
    service_ids = [c["service_id"] for c in calendars]

    trips = client.trips(service_ids)
    trip_ids = trips.keys()

    # trip_updates = client.trip_updates(trip_ids)
    stop_times_by_stop_id = client.stop_times(trip_ids)
    stops = client.stops()

    metra_stops_by_route_and_stop = defaultdict(lambda: {})
    for stop_id, stop_times in stop_times_by_stop_id.items():
        stop = stops[stop_id]

        for stop_time in stop_times:
            trip = trips[stop_time["trip_id"]]
            route = routes[trip["route_id"]]

            route_id = route["route_id"]
            if not ROUTES_AND_STOPS_TO_TRACK or route_id in ROUTES_AND_STOPS_TO_TRACK:
                stops_to_track = ROUTES_AND_STOPS_TO_TRACK[route_id]
                if not stops_to_track or stop_id in stops_to_track:
                    if stop_id not in metra_stops_by_route_and_stop[route_id]:
                        metra_stops_by_route_and_stop[route_id][stop_id] = MetraStop(route, stop)

                    metra_stops_by_route_and_stop[route_id][stop_id].add_time(trip["direction_id"], stop_time)

    metra_stops_by_route = {}
    for route_id, stops_by_stop_id in metra_stops_by_route_and_stop.items():
        metra_stops_by_route[route_id] = sorted(stops_by_stop_id.values(), key=lambda x: x.stop_sequence)
        for stop in metra_stops_by_route[route_id]:
            stop.sort_times()

    return render_template("metra.html",
        routes=routes,
        metra_stops_by_route=metra_stops_by_route,
        directions={
            0: "Outbound",
            1: "Inbound",
        }
    )
