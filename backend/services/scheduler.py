import asyncio
from routes import trip
from services.api_fetcher import fetch_prices
from services.decision_engine import evaluate
from services.booking_executor import execute_booking
from store.db import PRICE_HISTORY, TRIPS
from services.contract_service import build_itinerary_hash, commit_itinerary, release_funds
from dotenv import load_dotenv
load_dotenv()


async def run_trip(trip_id):
    PRICE_HISTORY[trip_id] = []

    while True:
        trip = TRIPS[trip_id]
        constraints = trip["constraints"]

        components = fetch_prices(constraints)

        total_cost = sum(c["price"] for c in components)
        PRICE_HISTORY[trip_id].append(total_cost)

        decision = evaluate(constraints, components, PRICE_HISTORY[trip_id])

        trip = TRIPS[trip_id]
        trip["components"] = components
        constraints = trip["constraints"]
        app_id = trip["contract"]["app_id"]
        user_address = trip["contract"]["user_address"]
        
        if decision["decision"] == "EXECUTE":
            booking_success = execute_booking(trip_id, components)
            if booking_success:
                itinerary_hash = build_itinerary_hash(trip_id, constraints, components)
                commit_tx_id = commit_itinerary(app_id, user_address, itinerary_hash)
                release_tx_id = release_funds(app_id, user_address)
                trip["status"] = "BOOKED"
                trip["contract"]["itinerary_hash"] = itinerary_hash
                trip["contract"]["itinerary_commit_tx_id"] = commit_tx_id
                trip["contract"]["release_tx_id"] = release_tx_id
                print(
                    "On-chain itinerary commitment complete -> "
                    f"trip_id: {trip_id}, app_id: {app_id}, itinerary_hash: {itinerary_hash}, "
                    f"commit_tx_id: {commit_tx_id}, release_tx_id: {release_tx_id}"
                )
                break

        await asyncio.sleep(5)  # polling interval