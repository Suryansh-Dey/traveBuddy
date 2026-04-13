import asyncio
from routes import trip
from services.api_fetcher import fetch_prices
from services.decision_engine import evaluate
from services.booking_executor import execute_booking
from store.db import PRICE_HISTORY, TRIPS
from services.contract_service import release_funds
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
                release_tx_id = release_funds(app_id, user_address)
                trip["status"] = "BOOKED"
                trip["contract"]["release_tx_id"] = release_tx_id
                break

        await asyncio.sleep(5)  # polling interval