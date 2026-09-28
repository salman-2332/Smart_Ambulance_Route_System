from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = Flask(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/traffic-route", methods=["POST"])
def traffic_route():

    if not GOOGLE_MAPS_API_KEY:
        return jsonify({
            "success": False,
            "error": "Google Maps API key is not configured."
        }), 500

    data = request.get_json()

    origin = data.get("origin")
    destination = data.get("destination")

    if not origin or not destination:
        return jsonify({
            "success": False,
            "error": "Origin and destination are required."
        }), 400

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "routes.distanceMeters,"
            "routes.duration,"
            "routes.staticDuration,"
            "routes.polyline.encodedPolyline"
        )
    }

    body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin["lat"],
                    "longitude": origin["lng"]
                }
            }
        },

        "destination": {
            "location": {
                "latLng": {
                    "latitude": destination["lat"],
                    "longitude": destination["lng"]
                }
            }
        },

        "travelMode": "DRIVE",

        "routingPreference": "TRAFFIC_AWARE",

        "computeAlternativeRoutes": False,

        "routeModifiers": {
            "avoidTolls": False,
            "avoidHighways": False,
            "avoidFerries": False
        },

        "languageCode": "en-US",

        "units": "METRIC"
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=15
        )

        result = response.json()

        if response.status_code != 200:

            return jsonify({
                "success": False,
                "error": result
            }), response.status_code

        if not result.get("routes"):

            return jsonify({
                "success": False,
                "error": "No route found."
            }), 404

        route = result["routes"][0]

        distance_meters = route.get(
            "distanceMeters",
            0
        )

        traffic_duration = route.get(
            "duration",
            "0s"
        )

        static_duration = route.get(
            "staticDuration",
            "0s"
        )

        def seconds_from_duration(value):

            return float(
                value.replace("s", "")
            )

        live_seconds = seconds_from_duration(
            traffic_duration
        )

        normal_seconds = seconds_from_duration(
            static_duration
        )

        traffic_delay = max(
            0,
            live_seconds - normal_seconds
        )

        return jsonify({

            "success": True,

            "distance_km":
                round(
                    distance_meters / 1000,
                    2
                ),

            "live_eta_minutes":
                round(
                    live_seconds / 60
                ),

            "normal_eta_minutes":
                round(
                    normal_seconds / 60
                ),

            "traffic_delay_minutes":
                round(
                    traffic_delay / 60
                ),

            "polyline":
                route["polyline"]["encodedPolyline"]

        })

    except requests.RequestException as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)