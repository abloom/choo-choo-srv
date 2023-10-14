from datetime import date, datetime
from pprint import pprint
from cache import cache
import requests

class MetraClient:
    base_headers = {'Accept': 'application/json'}

    def __init__(self, username: str, password: str, stops_by_route: dict[str, list[str]]) -> None:
        self.username = username
        self.password = password
        self.stops_by_route = stops_by_route
        self.route_ids = list(stops_by_route.keys())

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
                stop_ids_for_route = self.stops_by_route.get(route_id)
                for stop_time in trip_update["stop_time_update"]:
                    if not stop_ids_for_route or stop_time["stop_id"] in stop_ids_for_route:
                        stop_time_updates.append(stop_time)

                trip_update["stop_time_update"] = stop_time_updates

                if trip_update["stop_time_update"]:
                    trip_updates.append(update)
        
        return trip_updates

    @cache.cached(timeout=1440, key_prefix="metra_calendars")
    def calendars(self) -> dict:
        calendars = []
        today = datetime.now()
        day_of_week = today.strftime("%A").lower()
        for calendar in self._get("/schedule/calendar"):
            start_date = datetime.strptime(calendar["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(calendar["end_date"], "%Y-%m-%d")
            if start_date <= today <= end_date:
                if calendar[day_of_week]:
                    calendars.append(calendar)

        return calendars

    @cache.memoize(timeout=300)
    def trips(self, service_ids) -> dict:
        trips = {}
        for trip in self._get("/schedule/trips"):
            if not self.route_ids or (trip["route_id"] in self.route_ids):
                if trip["service_id"] in service_ids:
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
            if not self.route_ids or route["route_id"] in self.route_ids:
                routes[route["route_id"]] = route

        return routes

    @cache.memoize(timeout=300)
    def stop_times(self, trip_ids) -> dict:
        stop_times = {}
        for stop_time in self._get("/schedule/stop_times"):
            stop_id = stop_time["stop_id"]
            if stop_time["trip_id"] in trip_ids:
                if stop_id not in stop_times:
                    stop_times[stop_id] = []

                stop_times[stop_id].append(stop_time)

        return stop_times