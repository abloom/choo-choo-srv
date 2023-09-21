from cache import cache
import requests

ROUTES_AND_STOPS_TO_TRACK = {
    "UP-NW": ["JEFFERSONP"],
    # "UP-W": ["OTC"],
    # "BNSF": [],
}
ROUTE_IDS = ROUTES_AND_STOPS_TO_TRACK.keys()


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

    @cache.memoize(timeout=30)
    def trip_updates(self, trip_ids) -> list:
        trip_updates = []
        for update in self._get("/tripUpdates"):
            if update["is_deleted"]:
                next

            trip_update = update["trip_update"]
            trip = trip_update["trip"]
            if trip["trip_id"] in trip_ids:
                route_id = trip["route_id"]
                stop_time_updates = []
                stop_ids_for_route = ROUTES_AND_STOPS_TO_TRACK.get(route_id)
                for stop_time in trip_update["stop_time_update"]:
                    if not stop_ids_for_route or stop_time["stop_id"] in stop_ids_for_route:
                        stop_time_updates.append(stop_time)
                trip_update["stop_time_update"] = stop_time_updates

                if trip_update["stop_time_update"]:
                    trip_updates.append(update)
        
        return trip_updates

    @cache.cached(timeout=300, key_prefix="metra_trips")
    def trips(self) -> dict:
        trips = {}
        for trip in self._get("/schedule/trips"):
            if not ROUTE_IDS or (trip["route_id"] in ROUTE_IDS):
                trips[trip["trip_id"]] = trip

        return trips

    @cache.cached(timeout=300, key_prefix="metra_stops")
    def stops(self) -> dict:
        stops = {}
        for stop in self._get("/schedule/stops"):
            stops[stop["stop_id"]] = stop

        return stops

    @cache.cached(timeout=300, key_prefix="metra_routes")
    def routes(self) -> dict:
        routes = {}
        for route in self._get("/schedule/routes"):
            if not ROUTE_IDS or route["route_id"] in ROUTE_IDS:
                routes[route["route_id"]] = route

        return routes