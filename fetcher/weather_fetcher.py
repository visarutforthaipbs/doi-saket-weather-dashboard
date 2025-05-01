"""
Weather Data Fetcher for Doi Saket Weather Dashboard.

This script:
1. Fetches weather data from Weather Underground API
2. Enriches it with derived metrics
3. Stores the data in MongoDB Atlas
4. Runs on a schedule every 5 minutes
"""

import os
import time
import datetime
import logging
import requests
from dotenv import load_dotenv
import schedule
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from formulas import (
    heat_index,
    wet_bulb_temperature,
    fuel_moisture_index,
    fire_danger,
    heat_risk_level,
    calculate_pressure_trend
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Environment variables
WU_API_KEY = os.getenv('WU_API_KEY')
PWS_ID = os.getenv('PWS_ID', 'IDOISA4')  # Default to IDOISA4 if not specified
MONGODB_URI = os.getenv('MONGODB_URI')

# Set timezone
try:
    os.environ['TZ'] = os.getenv('TZ', 'Asia/Bangkok')
    time.tzset()
except AttributeError:
    # Windows doesn't have time.tzset()
    logger.warning("Unable to set timezone via time.tzset(). Make sure your system timezone is correct.")

# MongoDB setup
def get_mongodb_connection():
    """
    Create and return a MongoDB client connection.
    
    Returns:
        MongoClient: MongoDB client connection
    """
    try:
        client = MongoClient(MONGODB_URI)
        # Verify connection by pinging the server
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        return client
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {e}")
        raise

# Historical pressure readings (for trend calculation)
# Format: [(timestamp, pressure), ...]
historical_pressures = []
MAX_HISTORICAL_RECORDS = 50  # Keep last 50 readings


def fetch_weather_data():
    """
    Fetch current weather data from Weather Underground API.
    
    Returns:
        dict: Weather data or None if there was an error
    """
    if not WU_API_KEY:
        logger.error("Weather Underground API key not found in environment variables")
        return None

    url = f"https://api.weather.com/v2/pws/observations/current"
    params = {
        "stationId": PWS_ID,
        "format": "json",
        "units": "m",  # metric
        "apiKey": WU_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        return None


def process_weather_data(weather_data):
    """
    Process and enrich weather data with derived metrics.
    
    Args:
        weather_data (dict): Raw weather data from Weather Underground API
        
    Returns:
        dict: Enriched weather data
    """
    global historical_pressures
    
    if not weather_data or 'observations' not in weather_data or not weather_data['observations']:
        logger.error("Invalid weather data format")
        return None
    
    try:
        obs = weather_data['observations'][0]
        
        # Extract basic metrics
        timestamp = datetime.datetime.now()
        temp_c = obs.get('metric', {}).get('temp', 0)
        humidity = obs.get('humidity', 0)
        wind_speed = obs.get('metric', {}).get('windSpeed', 0)
        wind_gust = obs.get('metric', {}).get('windGust', 0)
        wind_dir = obs.get('winddir', 0)
        pressure = obs.get('metric', {}).get('pressure', 0)
        precip_rate = obs.get('metric', {}).get('precipRate', 0)
        precip_total = obs.get('metric', {}).get('precipTotal', 0)
        uv = obs.get('uv', 0)
        solar_radiation = obs.get('solarRadiation', 0)
        
        # Store current pressure for trend calculation
        current_pressure_entry = (timestamp.timestamp(), pressure)
        historical_pressures.append(current_pressure_entry)
        
        # Keep only the most recent records
        if len(historical_pressures) > MAX_HISTORICAL_RECORDS:
            historical_pressures = historical_pressures[-MAX_HISTORICAL_RECORDS:]
        
        # Calculate derived metrics
        heat_idx = heat_index(temp_c, humidity)
        wet_bulb = wet_bulb_temperature(temp_c, humidity)
        fmi = fuel_moisture_index(temp_c, humidity, precip_total)
        fire_danger_index, fire_risk = fire_danger(wind_speed, fmi)
        heat_risk = heat_risk_level(heat_idx)
        
        # Calculate pressure trend (3 hour)
        pressure_trend_3h = calculate_pressure_trend(
            current_pressure_entry, 
            historical_pressures[:-1]  # Exclude current reading
        )
        
        # Prepare enriched data
        enriched_data = {
            "timestamp": timestamp,
            "station_id": PWS_ID,
            "raw": {
                "temperature": temp_c,
                "humidity": humidity,
                "windSpeed": wind_speed,
                "windGust": wind_gust,
                "windDir": wind_dir,
                "pressure": pressure,
                "precipRate": precip_rate,
                "precipTotal": precip_total,
                "uv": uv,
                "solarRadiation": solar_radiation
            },
            "derived": {
                "heatIndex": heat_idx,
                "wetBulbTemp": wet_bulb,
                "fmi": fmi,
                "fireDanger": fire_danger_index,
                "pressureTrend3h": pressure_trend_3h
            },
            "risk": {
                "heatRisk": heat_risk,
                "fireRisk": fire_risk
            }
        }
        
        return enriched_data
    
    except KeyError as e:
        logger.error(f"Missing expected field in weather data: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing weather data: {e}")
        return None


def store_weather_data(enriched_data):
    """
    Store enriched weather data in MongoDB.
    
    Args:
        enriched_data (dict): Enriched weather data
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not enriched_data:
        return False
    
    try:
        client = get_mongodb_connection()
        db = client.weather_dashboard
        collection = db.pws_readings_enriched
        
        result = collection.insert_one(enriched_data)
        logger.info(f"Inserted weather data with ID: {result.inserted_id}")
        
        client.close()
        return True
    
    except Exception as e:
        logger.error(f"Error storing weather data: {e}")
        return False


def weather_job():
    """
    Main job function to fetch, process, and store weather data.
    """
    logger.info("Running weather data collection job")
    
    try:
        # Fetch data
        weather_data = fetch_weather_data()
        if not weather_data:
            logger.error("Failed to fetch weather data")
            return
        
        # Process data
        enriched_data = process_weather_data(weather_data)
        if not enriched_data:
            logger.error("Failed to process weather data")
            return
        
        # Store data
        if not store_weather_data(enriched_data):
            logger.error("Failed to store weather data")
            return
        
        logger.info("Weather data collection job completed successfully")
    
    except Exception as e:
        logger.error(f"Unexpected error in weather job: {e}")


def main():
    """
    Main function to schedule and run the weather collection job.
    """
    logger.info("Starting Doi Saket Weather Dashboard fetcher")
    
    # Check for required env vars
    if not WU_API_KEY:
        logger.error("WU_API_KEY environment variable is required")
        return
    
    if not MONGODB_URI:
        logger.error("MONGODB_URI environment variable is required")
        return
    
    # Run job immediately on startup
    weather_job()
    
    # Schedule job to run every 5 minutes
    schedule.every(5).minutes.do(weather_job)
    
    logger.info("Weather job scheduled to run every 5 minutes")
    
    # Run the scheduling loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Fetcher stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
            # Sleep a bit longer on error to avoid rapid failure cycles
            time.sleep(5)


if __name__ == "__main__":
    main()