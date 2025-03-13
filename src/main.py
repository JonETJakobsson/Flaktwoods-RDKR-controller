from machine import Pin, PWM, ADC, unique_id
import math
import utime
import dht
import asyncio
from vactrol import dualVactrol
from rdkr import Rdkr
import json
from ha_mqtt import setup_mqtt
import time

# Configuration
# Set aim temperature to match the
# heating/cooling system of your house
AIM_TEMP = 21
# Set dew point margin to negative to allow
#some extra cooling during night.
# Warning: can case condensation and halso halt
# the RDKR.
DEW_POINT_MARGIN = 1
# heating/cooling cost similar to rotor energy draw (14watts)
# 14 watts can heat 50l/s air aproximaty 0.875C
# If you use a heatpump with high efficiency, you can increase the relax temp 3-5x
RELAXING_TEMP = 0.87



# ----------------------------------------------------
# Constants for thermistors
T0 = 22 # 22C
R0 = 10000 # 10kOhms at 22 C
TCR = -750 #Ohms/C
#-----------------------------------------------------

# create a vactrol object
vac = dualVactrol(Pin(21), Pin(32), Pin(33), 17)
# create the rdkr object
rdkr = Rdkr(vac, T0, R0, TCR, Pin(25), Pin(26), Pin(27), Pin(15))
# start with rotor off
rdkr.rotor_off()


def calculate_dew_point(T, H):
    """
    Calculates the dew point in Celsius.
    """
    a = 17.27
    b = 237.7
    alpha = ((a * T) / (b + T)) + math.log(H / 100.0)
    dew_point = (b * alpha) / (a - alpha)
    
    return dew_point

def main():
    while True:
        # Attempt to connect with a timeout if wifi is lost
        timeout_seconds = 30
        start_time = time.time()
        while not wlan.isconnected() and time.time() - start_time < timeout_seconds:
            try:
                wlan.connect(ssid, password)
            except: "trying again"
            time.sleep(1)  # Wait for connection

        if wlan.isconnected():
            print("Wi-Fi connected:", wlan.ifconfig()[0])
            webrepl.start()
        else:
            print("Wi-Fi connection failed within the timeout.")

        # Reconnect strategy for MQTT setup
        if not group.is_connected:
            try:
                configuration_url = wlan.ifconfig()[0]
                group = setup_mqtt(mqtt_user, mqtt_password, f"http://{configuration_url}:8266")
            except Exception as e:
                print(f"Failed to connect to MQTT: {e}.")

        # Load all sensors
        rdkr.read_sensors()
        s = rdkr.extract_sensor_values()       
        
        dew_point = calculate_dew_point(s["return_air_temp"], s["return_air_hum"])
        print(f"dew point is: {dew_point}, given temperature {s["return_air_temp"]} and humidity {s["return_air_hum"]}")
        
        # Find the current heating/cooling need
        if s["return_air_temp"] > AIM_TEMP+RELAXING_TEMP:
            need = "cooling"
        elif s["return_air_temp"] < AIM_TEMP-RELAXING_TEMP:
            need = "heating"
        else:
            need = "no_need"
        
        # find rotor comparable effect
        if s["return_air_temp"] > s["fresh_air_temp"]:
            rotor = "heats"
        else:
            rotor = "cools"
        
        # find air closest to aim
        return_to_aim = s["return_air_temp"] - AIM_TEMP
        fresh_to_aim = s["fresh_air_temp"] - AIM_TEMP
        
        strategy_state = "strategy"
        rotor_state = "on"  # Rotor is always off when temperature is low
        if s["fresh_air_temp"] < 10:
            # Set r2 to the resistance measured of the termisor
            r2 = s["r2"]
            rdkr.vac.set_r2(r2)
            strategy_state ="fresh air temperature is below 10C. Letting RDKR decide"
        else:
            # If fresh air is lower than dew point, rotor on
            if s["fresh_air_temp"] < dew_point+DEW_POINT_MARGIN: 
                # Set r2 to the resistance measured of the termisor
                rdkr.rotor_on()
                strategy_state ="fresh air temperature is below dew point. turning rotor on"
            elif need == "cooling":
                if rotor == "heats":
                    rdkr.rotor_off()
                    rotor_state = "off"
                    strategy_state ="Cooling needed, turning rotor off"
                else:
                    rdkr.rotor_on()
                    strategy_state ="Cooling needed, turning rotor on"
            elif need == "heating":
                if rotor == "heats":
                    rdkr.rotor_on()
                    strategy_state ="Heating needed, turning rotor on"
                else:
                    rdkr.rotor_off()
                    rotor_state = "off"
                    strategy_state ="Heating needed, turning rotor off"
            else: #no need
                if abs(return_to_aim) < abs(fresh_to_aim):
                    rdkr.rotor_on()
                    strategy_state ="no heating or cooling needed, turning rotor on"
                else:
                    rdkr.rotor_off()
                    rotor_state = "off"
                    strategy_state ="no heating or cooling needed, turning rotor off"
        
        
        sensor_payload = rdkr.extract_sensor_payload()
        extra_payload = dict(
            rotor_state = rotor_state,
            strategy_state = strategy_state
            )
        
        # Generate MQTT payload
        payload = dict()

        payload.update(sensor_payload)
        payload.update(extra_payload)
        print(payload)
        group.publish_state(payload)
        time.sleep(120)

main()