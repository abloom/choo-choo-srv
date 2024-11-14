#!/usr/bin/env bash

USERNAME="76a3886e723cd66109aa26c6ce20d5eb"
PASSWORD="9486ca01a568ae076c7dc00b213da000"

# curl -s "https://${USERNAME}:${PASSWORD}@gtfsapi.metrarail.com/gtfs/positions" | \
#     jq 'map(select(.vehicle.trip.route_id == "UP-NW"))' | \
#     tee positions-up-nw.json

curl -s "https://${USERNAME}:${PASSWORD}@gtfsapi.metrarail.com/gtfs/tripUpdates" | \
    jq 'map(select(.trip_update.trip.route_id == "UP-NW"))' | \
    tee trip-updates-up-nw.json

curl -s "https://${USERNAME}:${PASSWORD}@gtfsapi.metrarail.com/gtfs/schedule/trips" | \
    jq 'map(select(.route_id == "UP-NW" and .direction_id == 1))' | \
    tee trip.json