#!/usr/bin/env python3
"""
PWM Fan Controller for Raspberry Pi

Controls a PWM fan connected to a Raspberry Pi GPIO pin based on CPU temperature.
Requires pigpio daemon running.

Usage:
    python3 pwm_fan_controller.py

Dependencies:
    - pigpio library
"""

import pigpio
import time
import sys
import logging
import signal
import os
import json

# --- Configuration ---
CONFIG_FILE = "fan_config.json"

DEFAULT_CONFIG = {
    "FAN_GPIO_PIN": 15,
    "TEMP_OFF": 35,
    "TEMP_FULL": 65,
    "PWM_MIN": 0,
    "PWM_MAX": 255,
    "SLEEP_INTERVAL": 10,
    "HYSTERESIS": 2,
    "TEMP_FILE": "/sys/class/thermal/thermal_zone0/temp"
}

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PWMFanController:
    def __init__(self, config):
        self.gpio_pin = config["FAN_GPIO_PIN"]
        self.temp_off = config["TEMP_OFF"]
        self.temp_full = config["TEMP_FULL"]
        self.pwm_min = config["PWM_MIN"]
        self.pwm_max = config["PWM_MAX"]
        self.sleep_interval = config["SLEEP_INTERVAL"]
        self.hysteresis = config["HYSTERESIS"]
        self.temp_file = config["TEMP_FILE"]

        self.last_set_pwm = -1
        self.last_checked_temp = 0
        self.pi = pigpio.pi()

        if not self.pi.connected:
            logging.error("Could not connect to pigpiod. Is it running?")
            sys.exit(1)

        if not (0 <= self.gpio_pin <= 27):
            logging.error("Invalid GPIO pin number.")
            sys.exit(1)

        self.pi.set_mode(self.gpio_pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.gpio_pin, 0)
        self.last_set_pwm = 0

        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        logging.info("Signal received, shutting down.")
        self.cleanup()
        sys.exit(0)

    def get_cpu_temperature(self):
        try:
            with open(self.temp_file, 'r') as f:
                return int(f.read().strip()) / 1000.0
        except FileNotFoundError:
            logging.error(f"Temperature file not found at {self.temp_file}")
        except ValueError:
            logging.error(f"Could not parse temperature from {self.temp_file}")
        except Exception as e:
            logging.error(f"Error reading temperature: {e}")
        return None

    def calculate_pwm(self, temp):
        if temp is None:
            return self.pwm_min

        if temp <= self.temp_off:
            return self.pwm_min
        elif temp >= self.temp_full:
            return self.pwm_max
        else:
            temp_range = float(self.temp_full - self.temp_off)
            pwm_range = float(self.pwm_max - self.pwm_min)
            pwm = int(((temp - self.temp_off) * pwm_range / temp_range) + self.pwm_min)
            return max(self.pwm_min, min(self.pwm_max, pwm))

    def run(self):
        logging.info("PWM Fan Controller started.")
        try:
            while True:
                cpu_temp = self.get_cpu_temperature()

                if cpu_temp is not None:
                    if abs(cpu_temp - self.last_checked_temp) >= (self.hysteresis / 2.0):
                        target_pwm = self.calculate_pwm(cpu_temp)

                        if target_pwm != self.last_set_pwm:
                            self.pi.set_PWM_dutycycle(self.gpio_pin, target_pwm)
                            logging.info(f"Temp: {cpu_temp:.1f}°C -> PWM set to {target_pwm}")
                            self.last_set_pwm = target_pwm
                            self.last_checked_temp = cpu_temp
                        else:
                            logging.debug(f"Temp: {cpu_temp:.1f}°C -> PWM unchanged ({self.last_set_pwm})")

                time.sleep(self.sleep_interval)

        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        if self.pi and self.pi.connected:
            try:
                logging.info("Setting fan PWM to 0 before exiting.")
                self.pi.set_PWM_dutycycle(self.gpio_pin, 0)
                self.pi.stop()
                logging.info("pigpio connection stopped.")
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")
        logging.info("Fan controller stopped.")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logging.info(f"Loaded configuration from {CONFIG_FILE}")
                return {**DEFAULT_CONFIG, **config}
        except Exception as e:
            logging.error(f"Error loading config file: {e}")
    logging.info("Using default configuration.")
    return DEFAULT_CONFIG

if __name__ == "__main__":
    config = load_config()
    controller = PWMFanController(config)
    controller.run()
