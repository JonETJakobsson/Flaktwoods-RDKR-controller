#from ml import linearRegressor
from linear import linearRegressor
from machine import PWM, ADC, Pin
import json
import asyncio
import math
import time

class dualVactrol:
    """Representation of a dual vactrol with self regulating resistance output"""
    
    def __init__(
        self,
        led_pin: Pin,
        lsr1_pin: Pin,
        lsr2_pin: Pin,
        init_pwm: int=17):
        """Instantiate a dual vactrol with photoresistor coeficients.
        
        Coeficients can be added manually, or calculated using the calibrate method.
        
        """

        self.led = PWM(led_pin, freq=int(1000), duty_u16=duty(init_pwm))
        self.lsr1 = ADC(lsr1_pin)
        self.lsr2 = ADC(lsr2_pin)

        # Load stored coeficients
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
            self.k1 = config.get('k1')
            self.m1 = config.get('m1')
            self.k2 = config.get('k2')
            self.m2 = config.get('m2')
    
    def run_calibration_sweep(self):
        """Run a pwm sweep and store lsr1 and lsr2 resistance"""
        # set LED to 0 and wait 1 second
        self.led.duty_u16(0)
        time.sleep(1)
        
        #Lists to store vlaues in
        idx_list = list()
        log_pwm_list = list()
        bit_list = list()
        pwm_list = list()
        r1 = list()
        r2 = list()
        r1_log = list()
        r2_log = list()
        
        for i in range(100):
            log_pwm = i / 50 # Creates a even distribution of log_pwm values (0-2)
            pwm = 10**(log_pwm) # calculate pwm from log_pwm
            bit_input = duty(pwm) # convert pwm to u16 bits
            self.led.duty_u16(bit_input)
            time.sleep(0.2)
            
            idx_list.append(i)
            log_pwm_list.append(log_pwm)
            bit_list.append(bit_input)
            pwm_list.append(pwm)
            r1.append(measure_res(self.lsr1))
            r2.append(measure_res(self.lsr2))
        
        # calculate log values for resistance
        for r in r1:
            r1_log.append(math.log10(r))
            
        for r in r2:
            r2_log.append(math.log10(r))
        
        # set led to 0 again
        self.led.duty_u16(0)
        return log_pwm_list, r1_log, r2_log
    
    def linear_regression(self, pwm: list, lsr: list, lr: float, max_iter: int):
        """find linear coeficients k and m for the data.

        returns: k, m"""
        print(len(pwm), len(lsr))
        
        # find start and stop for linear part
        start_idx = lsr.count(max(lsr)) + 5 # to get further intro linear part
        end_idx = - lsr.count(min(lsr)) - 5 # to get further intro linear part
        assert start_idx < len(pwm), "too few datapoint collected. Make sure lsr measurement is connected to vactrol"
        
        print(start_idx, end_idx)
        print(len(pwm[start_idx:end_idx]), len(lsr[start_idx:end_idx]))
        
        reg = linearRegressor(max_iter=max_iter, lr=lr)
        reg.fit(X=pwm[start_idx:end_idx], y=lsr[start_idx:end_idx])
        
        m = reg.coeficients[0]
        k= reg.coeficients[1]
        return k, m
        
    def calibrate(self, lr=0.1, max_iter=100, export_data=False):
        """calibrate photoresistors for correct resistance output of LSR2"""
        
        print("Running calibration sweep")
        log_pwm, log_r1, log_r2 = self.run_calibration_sweep()
        print(len(log_pwm), len(log_r1), len(log_r2))
        
        print("finding coeficients for lsr1")
        k1, m1 = self.linear_regression(pwm=log_pwm, lsr=log_r1, lr=lr, max_iter=max_iter)
 
        print("finding coeficients for lsr2")
        k2, m2 = self.linear_regression(pwm=log_pwm, lsr=log_r2, lr=lr, max_iter=max_iter)
        
        self.k1 = k1
        self.m1 = m1
        self.k2 = k2
        self.m2 = m2
        print(f"new coeficients added: k1: {k1}, m1: {m1}, k2: {k2}, m2: {m2}")
        
        if export_data:
            with open("calibration.csv", "w") as f:
                for i, _ in enumerate(log_pwm):
                    f.write(f"{log_pwm[i]},{log_r1[i]},{log_r2[i]}\n")
     
    def save_calibration(self):
        """Saves current coeficients to config.json
        (becomes defailt values in the future)"""
        
        with open("config.json", "r") as config_file:
            config = json.load(config_file)

        
        config["k1"] = self.k1
        config["m1"] = self.m1
        config["k2"] = self.k2
        config["m2"] = self.m2
        
        with open("config.json", "w") as config_file:
            json.dump(config, config_file)
        

    
    def set_r2(self, r2):
        """Sets resistance of LSR2 of the dual VACTROL by optimizing LSR1 resistance"""
        #print(f"r2: {r2}")
        # calculate the log10 representative of r2
        log_r2 = math.log10(r2)
        #print(f"log_r2: {log_r2}")
        # log_pwm for given log10(res) (initial starting point)
        log_pwm = (log_r2-self.m2)/self.k2
        #print(f"log_pwm: {log_pwm}")
        # calculate the pwm for given log(pwm)
        pwm = 10**log_pwm
        #print(f"pwm: {pwm}")
        # find lsr1 res corresponing to lsr2 res
        log_r1_aim = log_r2 + (self.m1-self.m2)
        #print(f"log_r1_aim: {log_r1_aim}")
        r1_aim = 10**log_r1_aim
        #print(f"r1_aim: {r1_aim}")
        
        error = 1000
        #print("minimizing error")
        while error > 500:
            self.led.duty_u16(duty(pwm))
            time.sleep_ms(200)
            r1 = measure_res(self.lsr1)
            error = r1 - r1_aim
            #print(f"Error: {error}")
            if abs(error) < 500:
                break
            elif error > 0: # high resistance -> needs higher pwm
                pwm = pwm + 0.1
            elif error < 0: # low resistance -> needs lower pwm
                pwm = pwm - 0.1
                
    def get_lsr1_res(self):
        r1 = measure_res(self.lsr1)
        return r1
    
    def get_lsr2_res(self):
        r2 = measure_res(self.lsr2)
        return r2


def duty(pwm: float) -> int:
    """calculate 16 bit value to set a % duty cycle
    pwm: float: 0-100
    """
    duty = pwm /100 * 65535
    return int(duty)


def measure_res(pin):
    """measure resistance of a voltage divider using a ADC pin.
    Voltage divider have r1 to 1kOhm and a voltage range of 0-1."""
    v0 = 5.0 # full range of voltage divider
    vmax = 1 # range of ADC pin
    r1 = 1000 # resistance of r1
    #Vr1 = pin.read_u16() * (vmax / 65535)
    Vr1 = pin.read_uv() / 1e6
    
    I: float = Vr1/r1
    Vrx: float = v0 - Vr1
    if I != 0:
        Rx: float = Vrx / I
    else:
        Rx = "inf"
    return Rx

