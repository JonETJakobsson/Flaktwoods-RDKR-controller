# From https://github.com/agners/micropython-ha-mqtt-device/tree/master

import ujson as json

class BaseEntity(object):

    def __init__(self, mqtt, name, component, object_id, node_id, discovery_prefix, extra_conf):
        self.mqtt = mqtt

        base_topic = discovery_prefix + b'/' + component + b'/'
        if node_id:
            base_topic += node_id + b'/'
        base_topic += object_id + b'/'

        self.config_topic = base_topic + b'config'
        self.state_topic = base_topic + b'state'

        self.config = {"name": name, "state_topic": self.state_topic}
        if extra_conf:
            self.config.update(extra_conf)
        self.mqtt.publish(self.config_topic, bytes(json.dumps(self.config), 'utf-8'), True, 1)

    def remove_entity(self):
        self.mqtt.publish(self.config_topic, b'', 1)

    def publish_state(self, state):
        self.mqtt.publish(self.state_topic, state)

class BinarySensor(BaseEntity):

    def __init__(self, mqtt, name, object_id, node_id=None,
            discovery_prefix=b'homeassistant', extra_conf=None):

        super().__init__(mqtt, name, b'binary_sensor', object_id, node_id,
                discovery_prefix, extra_conf)

    def publish_state(self, state):
        self.mqtt.publish(self.state_topic, b'ON' if state else b'OFF')
            
    def on(self):
        self.publish_state(True)

    def off(self):
        self.publish_state(False)

class Sensor(BaseEntity):

    def __init__(self, mqtt, name, object_id, node_id=None,
            discovery_prefix=b'homeassistant', extra_conf=None):

        super().__init__(mqtt, name, b'sensor', object_id, node_id,
                discovery_prefix, extra_conf)

class Text(BaseEntity):
    def __init__(self, mqtt, name, object_id, node_id=None,
            discovery_prefix=b'homeassistant', extra_conf=None):

        super().__init__(mqtt, name, b'text', object_id, node_id,
                discovery_prefix, extra_conf)

class EntityGroup(object):

    def __init__(self, mqtt, node_id, discovery_prefix=b'homeassistant',
            extra_conf=dict()):
        self.mqtt = mqtt
        self.node_id = node_id
        self.discovery_prefix = discovery_prefix
        # Group wide extra conf, gets passed to sensors
        self.extra_conf = extra_conf
        # Read state_topic from config if provided
        if "state_topic" in extra_conf:
            self.state_topic = extra_conf["state_topic"]
        else:
            self.state_topic = discovery_prefix + b'/sensor/' + node_id + b'/state'
            extra_conf["state_topic"] = self.state_topic
        self.entities = []

    def _update_extra_conf(self, extra_conf):
        if "value_template" not in extra_conf:
            raise Exception("Groupped sensors need value_template to be set.")
        extra_conf.update(self.extra_conf)

    def create_binary_sensor(self, name, object_id, extra_conf):
        self._update_extra_conf(extra_conf)
        bs = BinarySensor(self.mqtt, name, object_id, self.node_id,
                self.discovery_prefix, extra_conf)
        self.entities.append(bs)
        return bs

    def create_sensor(self, name, object_id, extra_conf):
        self._update_extra_conf(extra_conf)
        s = Sensor(self.mqtt, name, object_id, self.node_id,
                self.discovery_prefix, extra_conf)
        self.entities.append(s)
        return s

    def create_text(self, name, object_id, extra_conf):
        self._update_extra_conf(extra_conf)
        t = Text(self.mqtt, name, object_id, self.node_id,
                self.discovery_prefix, extra_conf)
        self.entities.append(t)
        return t
    
    def publish_state(self, state):
        self.mqtt.publish(self.state_topic, bytes(json.dumps(state), 'utf-8'))

    def remove_group(self):
        for e in self.entities:
            e.remove_entity()
            


# Added locig for connecting and returning a mqtt group
def setup_mqtt(username: str, password: str, configuration_url: str) -> EntityGroup:
    """Sets up the device and add all sensors.
    Return the EntityObject that is used to update sensor readings."""
    
    from mqtt_robust import MQTTClient
    import binascii
    from machine import unique_id
    serial_number = str(binascii.hexlify(unique_id()), "utf-8")
    client_id = "RDKR_" + serial_number[-5:]

    mqtt = MQTTClient(bytes(client_id, "utf-8"), "homeassistant.local", user=username, password=password, keepalive=600)

    print(f"connecting to mqtt with client id {client_id}")
    try:
        mqtt.connect()
        print("connection successful")
    except Exception as e:
        print(f"Failed to connect to MQTT: {e}")
    

    device_config = dict(
        identifiers = [client_id],
        name = client_id,
        manufacturer = "Jon Jakobsson",
        configuration_url = configuration_url,
        model = "RDKR controller",
        hw_version = "v1.0",
        serial_number = serial_number
    )
    
    common_config = dict(
        device = device_config)

    group = EntityGroup(mqtt, bytes(client_id, "utf-8"), extra_conf=common_config)


    for sensor in ["fresh_air", "supply_air", "return_air", "exhaust_air"]:
        temperature_config = {
            "unit_of_measurement": "°C",
            "device_class": "Temperature",
            "value_template": "{{ " + f"value_json.{sensor}_temp" + "}}",
            "unique_id": f"{client_id}_{sensor}_temp",
            "state_class": "measurement"
            }
        group.create_sensor(bytes(f"{sensor}_temp", "utf-8"), bytes(f"{sensor}_temp_id", "utf-8"), extra_conf=temperature_config)
        
        humidity_config = {
            "unit_of_measurement": "%",
            "device_class": "Humidity",    
            "value_template": "{{ " + f"value_json.{sensor}_hum" + "}}",
            "unique_id": f"{client_id}_{sensor}_hum",
            "state_class": "measurement"
        }
        group.create_sensor(bytes(f"{sensor}_hum", "utf-8"), bytes(f"{sensor}_hum_id", "utf-8"), extra_conf=humidity_config)
    
    # resistor sensor
    sensor = "r2"
    resistance_config = {
        "unit_of_measurement": "Ohm",
        "device_class": "Voltage",
        "value_template": "{{ " + f"value_json.r2" + "}}",
        "unique_id": f"{client_id}_{sensor}_res",
        "state_class": "measurement"
        }
    group.create_sensor(bytes("r2", "utf-8"), bytes("r2_id", "utf-8"), extra_conf=resistance_config)
    
    # rotor state
    rotor_state_config = {
    "payload_on": "on",  # Payload value indicating the motor is running
    "payload_off": "off",  # Payload value indicating the motor is stopped
    "device_class": "running",  # Set the device class to "motor"
    "value_template": "{{ " + f"value_json.rotor_state" + "}}",
    "unique_id": f"{client_id}_rotor_state",  # Unique ID for the sensor
    #"state_class": "measurement",  # Set the state class to "measurement"
    }
    group.create_binary_sensor(bytes("rotor_state", "utf-8"), bytes("rotor_state_id", "utf-8"), extra_conf=rotor_state_config)
    
    
    # strategy state
    strategy_state_config = {
    "value_template": "{{ " + f"value_json.strategy_state" + "}}",
    "unique_id": f"{client_id}_strategy_state",  # Unique ID for the sensor
    }
    group.create_sensor(bytes("strategy_state", "utf-8"), bytes("strategy_state_id", "utf-8"), extra_conf=strategy_state_config)
    
    return group

