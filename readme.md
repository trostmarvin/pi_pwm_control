# Raspberry Pi PWM Fan Control using Python, pigpio, and systemd

This guide explains how to efficiently control a 4-pin PWM fan (like a Noctua NF-A4x10 5V PWM) connected to a Raspberry Pi based on CPU temperature. It uses a Python script that runs as a background service managed by `systemd`, interacting with the `pigpio` library.

## Why this Method?

This method uses a **long-running Python script (daemon)** managed by **`systemd`**, the standard Linux service manager. This approach is generally more efficient and robust for continuous background tasks:

*   **Efficient:** Only one process runs continuously, minimizing the overhead of starting/stopping scripts.
*   **Responsive:** Can check temperature and adjust the fan more frequently (e.g., every 5-10 seconds) without significant impact.
*   **Stateful:** The script keeps track of the last fan speed set, only sending commands to `pigpio` when a change is actually needed, reducing unnecessary GPIO operations.
*   **Robust:** `systemd` handles starting the script on boot and can automatically restart it if it crashes.
*   **Clean:** Avoids cluttering the user's `crontab`.

## Prerequisites

*   Raspberry Pi (any model with GPIO pins)
*   Raspberry Pi OS (or a similar Debian-based Linux distribution with `systemd`)
*   Python 3 (usually pre-installed on Raspberry Pi OS)
*   A 4-pin PWM fan (this guide uses a 5V Noctua fan as an example)
*   Internet connection (for installing software)
*   Basic familiarity with the Linux command line.

## (Optional) Hardware Setup: Connecting the Fan

**Warning:** Continue at your own risk! Modifying fan connectors can void the warranty and potentially damage your fan or Raspberry Pi if done incorrectly. Proceed with caution and double-check your connections. Discharge static electricity before handling components.

**Info:** You can also use jumper wires to connect your fan as you want.

Standard 4-pin PWM Fan Pinout:
1.  **Black:** Ground (GND)
2.  **Yellow:** +5V Power (Important to get the +5V Version, as the Pi only supply 5V)
3.  **Green:** Tacho / RPM Signal (reports fan speed back)
4.  **Blue:** PWM Control Signal

*   Check out the Noctua Pin Layout here: [https://faqs.noctua.at/en/support/solutions/articles/101000081757-what-pin-configuration-do-noctua-fans-use-](https://faqs.noctua.at/en/support/solutions/articles/101000081757-what-pin-configuration-do-noctua-fans-use-)

Raspberry Pi Target Pins (using BCM numbering):
*   **Pin 4:** 5V Power
*   **Pin 6:** Ground
*   **Pin 8:** GPIO 14 (to read the Tacho signal - not used in this script)
*   **Pin 10:** GPIO 15 (for PWM Control)

*   See the Raspberry Pi Pin Layout at [https://pinout.xyz/](https://pinout.xyz/)

**Goal:** Swap Ground and +5V Pin on the Noctua Fan to simply plug the connector on the Pi.

**Swapping Pins on the Noctua Connector:**

Carefully remove both the black (Ground) and yellow (+5V) wires from the fan's connector housing using a small pin or tool to lift the plastic retaining tab for each wire. Swap their positions and re-insert them, ensuring they click securely. Now that the black and yellow cables are swapped, the connector layout (Yellow, Black, Green, Blue) should align correctly with Raspberry Pi pins 4, 6, 8, and 10 respectively.

**Connect to Pi:** Once rearranged, align the connector so the Yellow wire goes to Pin 4, Black to Pin 6, Green to Pin 8, and Blue to Pin 10. Gently push the connector onto the header pins.

![raspi_noctua_setup](https://github.com/user-attachments/assets/e5b4b009-8df0-4885-8763-725c540dcc1a)

## Software Setup

1.  **Update Package List:**
    ```bash
    sudo apt update
    ```

2.  **Install pigpio and Python Client:** This installs the `pigpio` daemon and the Python library needed to interact with it.
    ```bash
    sudo apt install pigpio python3-pigpio
    ```

3.  **Enable and Start the pigpio Daemon:** The Python script needs the `pigpiod` service running in the background. Enabling ensures it starts on boot.
    ```bash
    sudo systemctl enable pigpiod
    sudo systemctl start pigpiod
    ```

4.  **Verify pigpio Daemon Status:** Check that the service is running.
    ```bash
    sudo systemctl status pigpiod
    ```
    You should see "active (running)". Press `q` to exit the status view.

## The Python Control Script
1. **Download the Script File:** Use wget and download the script directly.
    ```bash
    cd ~
    wget https://raw.githubusercontent.com/trostmarvin/simple-rpi-fan-control/refs/heads/main/pwm_fan_control.py
    ```

2. **Create the Script File manually:** Use a text editor like `nano` to create the script in your home directory (or another location of your choice).
    ```bash
    nano  ~/pwm_fan_control.py
    ```

    **Paste the Script Code:** Copy and paste the following Python code into the editor.

3.  **Customize (Optional):**
    *   Inside the script, adjust `FAN_GPIO_PIN` if you used a different GPIO pin.
    *   Modify `TEMP_OFF`, `TEMP_FULL`, `SLEEP_INTERVAL`, and `HYSTERESIS` variables to fine-tune the fan behavior.

4.  **Save and Exit:** Press `Ctrl+X`, then `Y`, then `Enter` to save the file in `nano`.

5.  **Test Manually (Optional):** You can run the script directly from your terminal to see if it works and prints any errors. Press `Ctrl+C` to stop it.
    ```bash
    python3 ~/pwm_fan_control.py
    ```

## Automating with `systemd`

We will create a `systemd` service file to manage the Python script, allowing it to run automatically on boot and be controlled like other system services.

1.  **Create the Service File:** Use `nano` with `sudo` to create a service file in the systemd directory.
    ```bash
    sudo nano /etc/systemd/system/pwm-fan-control.service
    ```

2.  **Paste Service Configuration:** Copy and paste the following content into the editor.

    ```ini
    [Unit]
    Description=PWM Fan Control Service for Raspberry Pi
    After=network.target pigpiod.service
    Requires=pigpiod.service

    [Service]
    # Adjust the path to your script and your username
    ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/pwm_fan_control.py
    WorkingDirectory=/home/YOUR_USERNAME/
    StandardOutput=inherit
    StandardError=inherit
    Restart=always
    User=YOUR_USERNAME

    [Install]
    WantedBy=multi-user.target
    ```

    *   **IMPORTANT:** Replace `YOUR_USERNAME` in **both** the `ExecStart` and `User` lines with your actual username (e.g., `pi`). Ensure the path in `ExecStart` matches where you saved your Python script.

3.  **Save and Exit:** Press `Ctrl+X`, then `Y`, then `Enter`.

4.  **Reload systemd:** Make systemd aware of the new service file.
    ```bash
    sudo systemctl daemon-reload
    ```

5.  **Enable the Service:** This makes the service start automatically on boot.
    ```bash
    sudo systemctl enable pwm-fan-control.service
    ```

6.  **Start the Service:** Start the fan control service immediately.
    ```bash
    sudo systemctl start pwm-fan-control.service
    ```

7.  **Check Service Status:** Verify that the service is running correctly.
    ```bash
    sudo systemctl status pwm-fan-control.service
    ```
    Look for "active (running)". You might also see the initial print statements from the script. Press `q` to exit the status view.

**Managing the Service:**

*   **Stop:** `sudo systemctl stop pwm-fan-control.service`
*   **Start:** `sudo systemctl start pwm-fan-control.service`
*   **Restart:** `sudo systemctl restart pwm-fan-control.service`
*   **Disable (prevent start on boot):** `sudo systemctl disable pwm-fan-control.service`
*   **View Logs:** `sudo journalctl -u pwm-fan-control.service -f` (Use `-f` to follow logs live, press `Ctrl+C` to stop following)

## Testing

1.  **Check Service Status:** Use `sudo systemctl status pwm-fan-control.service` to ensure it's active.
2.  **Check Temperature:** See the current CPU temperature:
    ```bash
    cat /sys/class/thermal/thermal_zone0/temp
    # Divide by 1000 for Celsius
    ```
3.  **Increase Load (Optional):** To test the fan speeding up, put the CPU under load:
    ```bash
    # Install stress tool if you don't have it
    # sudo apt install stress
    # Run stress test on all available cores (e.g., 4) for 60 seconds
    stress --cpu $(nproc) --timeout 60
    ```
    Monitor the fan speed while the temperature increases. Check the service logs (`journalctl -u pwm-fan-control.service`) if you uncommented the print statements in the script.
4.  **Check Logs:** Use `sudo journalctl -u pwm-fan-control.service` to see any output or error messages from the script.

## Troubleshooting

*   **Fan doesn't spin / Service Fails:**
    *   Check wiring carefully.
    *   Ensure `pigpiod` is running: `sudo systemctl status pigpiod`.
    *   Verify the correct `FAN_GPIO_PIN` is set in the Python script.
    *   Check the service status: `sudo systemctl status pwm-fan-control.service`.
    *   Examine the service logs for errors: `sudo journalctl -u pwm-fan-control.service`. Look for Python errors, "Could not connect to pigpiod", permission issues, or temperature file reading errors.
    *   Ensure the `User` and script path in `pwm-fan-control.service` are correct and match your setup. Reload (`sudo systemctl daemon-reload`) and restart the service after edits.
    *   Run the Python script manually (`python3 /path/to/script.py`) to see errors directly.
*   **"Error: Could not connect to pigpiod"**: Make sure `pigpiod` is installed, enabled, and started. Check that the `pwm-fan-control.service` starts *after* `pigpiod.service` (as defined in the `[Unit]` section).
*   **Permission Errors in Logs:** Ensure the `User` specified in the service file has the necessary permissions (usually handled correctly if `pigpiod` runs as root). Check permissions on the script file itself (`ls -l /path/to/script.py`).

