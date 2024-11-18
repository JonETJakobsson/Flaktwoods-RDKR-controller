
class Rdkr:
    def __init__(
        self,
        vac: dualVactrol,
        T0,
        R0,
        TCR,
        fa_pin: Pin,
        sa_pin: Pin,
        ra_pin: Pin,
        ea_pin: Pin):
        
        from dht import DHT22
        
        self.vac = vac
        self.T0 = T0
        self.R0 = R0
        self.TCR = TCR
        # DHT sensors
        self.fresh_air_dht = DHT22(fa_pin)
        self.supply_air_dht = DHT22(sa_pin)
        self.return_air_dht = DHT22(ra_pin)
        self.exhaust_air_dht = DHT22(ea_pin)

    # sensors with mqtt matched output
    def read_sensors(self):
        """reads all sensors"""
        try:
            self.fresh_air_dht.measure()
        except: "issue with FA DHT"
        try:
            self.supply_air_dht.measure()
        except: "issue with SA DHT"
        try:
            self.return_air_dht.measure()
        except: "issue with RA DHT"
        try:
            self.exhaust_air_dht.measure()
        except: "issue with EA DHT"
        
    def extract_sensor_values(self) -> dict[str:float]:
        # reads all sensors
        sensors = dict(
            fresh_air_temp = self.fresh_air_dht.temperature(),
            supply_air_temp = self.supply_air_dht.temperature(),
            return_air_temp = self.return_air_dht.temperature(),
            exhaust_air_temp = self.exhaust_air_dht.temperature(),
            fresh_air_hum = self.fresh_air_dht.humidity(),
            supply_air_hum = self.supply_air_dht.humidity(),
            return_air_hum = self.return_air_dht.humidity(),
            exhaust_air_hum = self.exhaust_air_dht.humidity(),
            r2 = self.vac.get_lsr2_res()
            )
        return sensors
    
    def extract_sensor_payload(self) -> dict[str:str]:
        # Make float version of payload
        sensors = self.extract_sensor_values()
        payload = {k: str(v) for (k, v) in sensors.items()}
        return payload
        
    
    # functions related to temperature/resistance conversion

    def calculate_temperature(self, r1):
        """Calculate the temperature represented by a resistance value"""
        delta_r = r1-self.R0
        T1 = self.T0 + delta_r/self.TCR
        return T1

    def calculate_resistance(self, T1):
        """Calculate the resistant value representing a specific temperature"""
        delta_t = T1-self.T0
        delta_r = delta_t*self.TCR
        r1 = self.R0+delta_r
        return r1

    def set_out_temp(self, t2):
        # set LSR2 to corresponding temperature
        r2 = self.calculate_resistance(float(t2))
        self.vac.set_r2(r2)

    def rotor_on(self):
        # set t2 to 10C to force rotor to run
        self.set_out_temp(10)
        print("rotor is on")
        
    def rotor_off(self):
        # set t2 to 22C to turn the rotor off
        self.set_out_temp(22)
        print("rotor is off")
