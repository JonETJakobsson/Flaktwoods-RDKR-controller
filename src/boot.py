import network
import json
import time
import webrepl

# Read configuration from config.json
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
        ssid = config.get('ssid')
        password = config.get('password')
        mqtt_user = config.get('mqtt_user')
        mqtt_password = config.get('mqtt_password')
except OSError as e:
    print(f"Could not find config.json: {e}")
    
# Set up Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(False)
wlan.active(True)


# Add your application-specific logic in main.py
