#!/usr/bin/env python3
import pigpio
import time
import sys
import os

# --- Configuration ---
# Set the GPIO pin connected to the fan's PWM control wire (BLUE wire).
# Your setup: PIN 10 = GPIO 15 (BCM numbering)
FAN_GPIO_PIN = 15

# Set temperature thresholds in Celsius
TEMP_OFF = 35  # Temperature below which the fan is off (PWM 0)
TEMP_FULL = 65 # Temperature above which the fan is full speed (PWM 255)

# PWM range for pigpio (0 = off, 255 = full speed)
PWM_MIN = 0
PWM_MAX = 255

# How often to check the temperature (in seconds)
SLEEP_INTERVAL = 10

# Optional: Hysteresis temperature range (degrees C)
# Fan speed will only change if temp moves outside of (last_temp +/- HYSTERESIS/2)
# Helps prevent rapid cycling. Set to 0 to disable.
HYSTERESIS = 2
# --- End Configuration ---

# Path to the CPU temperature file
TEMP_FILE = "/sys/class/thermal/thermal_zone0/temp"

last_set_pwm = -1 # Initialize to a value that will force the first update
last_checked_temp = 0 # For hysteresis calculation

def get_cpu_temperature():
    """Reads CPU temperature from the system file."""
    try:
        with open(TEMP_FILE, 'r') as f:
            return int(f.read().strip()) / 1000.0
    except FileNotFoundError:
        print(f"Error: Temperature file not found at {TEMP_FILE}", file=sys.stderr)
        return None
    except ValueError:
        print(f"Error: Could not parse temperature from {TEMP_FILE}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading temperature: {e}", file=sys.stderr)
        return None

def calculate_pwm(temp):
    """Calculates the target PWM value based on temperature."""
    if temp is None:
        return PWM_MIN # Default to off if temp reading fails

    if temp <= TEMP_OFF:
        return PWM_MIN
    elif temp >= TEMP_FULL:
        return PWM_MAX
    else:
        # Linear interpolation
        temp_range = float(TEMP_FULL - TEMP_OFF)
        pwm_range = float(PWM_MAX - PWM_MIN)
        pwm = int(((temp - TEMP_OFF) * pwm_range / temp_range) + PWM_MIN)
        # Clamp value
        return max(PWM_MIN, min(PWM_MAX, pwm))

def main():
    global last_set_pwm, last_checked_temp

    print("Starting PWM Fan Controller...")
    try:
        pi = pigpio.pi()
        if not pi.connected:
            print("Error: Could not connect to pigpiod. Is it running?", file=sys.stderr)
            sys.exit(1)

        # Set GPIO mode just in case
        pi.set_mode(FAN_GPIO_PIN, pigpio.OUTPUT)
        # Ensure fan starts in a known state (off)
        pi.set_PWM_dutycycle(FAN_GPIO_PIN, 0)
        last_set_pwm = 0
        print(f"Initialized GPIO {FAN_GPIO_PIN}, starting control loop.")

    except Exception as e:
        print(f"Error initializing pigpio: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        while True:
            cpu_temp = get_cpu_temperature()

            if cpu_temp is not None:
                # Apply hysteresis: Only calculate new PWM if temp changed enough
                if abs(cpu_temp - last_checked_temp) >= (HYSTERESIS / 2.0):
                    target_pwm = calculate_pwm(cpu_temp)

                    # Only update PWM if the target value has changed
                    if target_pwm != last_set_pwm:
                        pi.set_PWM_dutycycle(FAN_GPIO_PIN, target_pwm)
                        last_set_pwm = target_pwm
                        last_checked_temp = cpu_temp # Update temp threshold for hysteresis
                        # print(f"Temp: {cpu_temp:.1f}C -> Setting PWM: {target_pwm}") # Uncomment for debug logging
                    # else: # Uncomment for debug logging
                        # print(f"Temp: {cpu_temp:.1f}C -> PWM unchanged ({last_set_pwm})")

            # Wait before next check
            time.sleep(SLEEP_INTERVAL)

    except KeyboardInterrupt:
        print("\nStopping fan control (KeyboardInterrupt).")
    except Exception as e:
        print(f"\nAn error occurred: {e}", file=sys.stderr)
    finally:
        # Clean up: Set fan to off before exiting
        if pi and pi.connected:
            try:
                print("Setting fan PWM to 0 before exiting.")
                pi.set_PWM_dutycycle(FAN_GPIO_PIN, 0)
                pi.stop()
                print("pigpio connection stopped.")
            except Exception as e:
                print(f"Error during cleanup: {e}", file=sys.stderr)
        print("Fan controller stopped.")

if __name__ == "__main__":
    main()
