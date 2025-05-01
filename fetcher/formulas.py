"""
Weather calculation formulas for Doi Saket Weather Dashboard.

This module contains formulas for calculating derived weather metrics:
- Heat Index (Rothfusz - metric)
- Wet Bulb Temperature (Stull 2011)
- Fuel Moisture Index (FMI)
- Fire Danger Index
"""

import math


def heat_index(temperature_c, humidity):
    """
    Calculate the Heat Index using the Rothfusz regression formula (metric).
    
    Args:
        temperature_c (float): Temperature in Celsius
        humidity (float): Relative humidity (%)
        
    Returns:
        float: Heat Index in Celsius
    """
    # Convert Celsius to Fahrenheit for the formula
    temperature_f = (temperature_c * 9/5) + 32
    
    # Rothfusz regression formula
    hi_f = -42.379 + (2.04901523 * temperature_f) + (10.14333127 * humidity)
    hi_f -= (0.22475541 * temperature_f * humidity)
    hi_f -= (6.83783e-3 * temperature_f**2)
    hi_f -= (5.481717e-2 * humidity**2)
    hi_f += (1.22874e-3 * temperature_f**2 * humidity)
    hi_f += (8.5282e-4 * temperature_f * humidity**2)
    hi_f -= (1.99e-6 * temperature_f**2 * humidity**2)
    
    # Adjustment for very high/low humidity and temperature
    if humidity < 13 and temperature_f >= 80 and temperature_f <= 112:
        adjustment = ((13 - humidity) / 4) * math.sqrt((17 - abs(temperature_f - 95)) / 17)
        hi_f -= adjustment
    elif humidity > 85 and temperature_f >= 80 and temperature_f <= 87:
        adjustment = ((humidity - 85) / 10) * ((87 - temperature_f) / 5)
        hi_f += adjustment
    
    # Convert back to Celsius
    hi_c = (hi_f - 32) * 5/9
    
    # If temperature is low, heat index is just the temperature
    if temperature_c < 26.7:  # 80°F
        return temperature_c
    
    return round(hi_c, 1)


def wet_bulb_temperature(temperature_c, humidity):
    """
    Calculate the Wet Bulb Temperature using Stull's formula (2011).
    
    Args:
        temperature_c (float): Temperature in Celsius
        humidity (float): Relative humidity (%)
        
    Returns:
        float: Wet Bulb Temperature in Celsius
    """
    # Stull's formula (2011)
    t = temperature_c
    rh = humidity
    
    wet_bulb = t * math.atan(0.151977 * math.sqrt(rh + 8.313659)) 
    wet_bulb += math.atan(t + rh) - math.atan(rh - 1.676331)
    wet_bulb += 0.00391838 * (rh)**(3/2) * math.atan(0.023101 * rh) - 4.686035
    
    return round(wet_bulb, 1)


def fuel_moisture_index(temperature_c, humidity, precipitation_total=0):
    """
    Calculate the Fuel Moisture Index (FMI).
    
    Higher FMI indicates wetter conditions, less fire risk.
    
    Args:
        temperature_c (float): Temperature in Celsius
        humidity (float): Relative humidity (%)
        precipitation_total (float): Total precipitation in mm
        
    Returns:
        float: Fuel Moisture Index
    """
    # Basic FMI calculation with temperature and humidity
    base_fmi = 10 - (0.25 * (temperature_c - 15)) + (0.08 * humidity)
    
    # Add precipitation factor (more rain = higher FMI)
    rain_factor = min(5, precipitation_total * 0.5)  # Cap at +5
    
    fmi = base_fmi + rain_factor
    
    # Ensure FMI stays within reasonable bounds (0-10)
    return max(0, min(10, round(fmi, 1)))


def fire_danger(wind_speed, fmi):
    """
    Calculate the Fire Danger Index.
    
    Args:
        wind_speed (float): Wind speed in km/h
        fmi (float): Fuel Moisture Index
        
    Returns:
        float: Fire Danger Index
        str: Risk level (Low, Moderate, High)
    """
    # Use max to avoid division by zero
    fire_danger_index = (max(wind_speed, 1) * 10) / max(fmi, 0.1)
    fire_danger_index = round(fire_danger_index, 1)
    
    # Determine risk level
    if fire_danger_index < 5:
        risk_level = "Low"
    elif fire_danger_index < 15:
        risk_level = "Moderate"
    else:
        risk_level = "High"
    
    return fire_danger_index, risk_level


def heat_risk_level(heat_index):
    """
    Determine the heat risk level based on heat index.
    
    Args:
        heat_index (float): Heat index in Celsius
        
    Returns:
        str: Risk level (Comfort, Caution, Extreme, Danger)
    """
    if heat_index < 27:
        return "Comfort"
    elif heat_index < 32:
        return "Caution"
    elif heat_index < 41:
        return "Extreme"
    else:
        return "Danger"


def calculate_pressure_trend(current_pressure, historical_pressures):
    """
    Calculate the 3-hour pressure trend.
    
    Args:
        current_pressure (float): Current barometric pressure in hPa
        historical_pressures (list): List of historical pressure readings
            with timestamps, ordered newest to oldest
            
    Returns:
        float: Pressure change over 3 hours (hPa)
    """
    # If we don't have enough historical data, return 0
    if not historical_pressures:
        return 0
    
    # Find the reading closest to 3 hours ago
    # Assuming historical_pressures is a list of (timestamp, pressure) tuples
    three_hours_ago = None
    for timestamp, pressure in historical_pressures:
        time_diff = current_pressure[0] - timestamp  # timestamp diff in seconds
        if time_diff >= 10800:  # 3 hours = 10800 seconds
            three_hours_ago = pressure
            break
    
    if three_hours_ago is None:
        return 0
    
    # Calculate the trend (positive means rising pressure)
    trend = round(current_pressure[1] - three_hours_ago, 1)
    
    return trend