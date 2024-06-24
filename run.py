import json
import time
import threading
import numpy as np
from mss import mss as mss_module
import kmNet
from ctypes import WinDLL
import sys

def exiting():
    try:
        exec(type((lambda: 0).__code__)(0, 0, 0, 0, 0, 0, b'\x053', (), (), (), '', '', 0, b''))
    except:
        try:
            sys.exit()
        except:
            raise SystemExit

class TriggerBot:
    def __init__(self):
        self.exit_program = False
        self.is_scoped = False
        self.target_detected = False

        with open('config.json') as json_file:
            data = json.load(json_file)

        try:
            self.ip = data["ip"]
            self.port = data["port"]
            self.uid = data["uid"]
            self.trigger_delay = data["trigger_delay"]
            self.base_delay = data["base_delay"]
            self.color_tolerance = data["color_tolerance"]
            self.R, self.G, self.B = data["target_color"]
            self.scope_R, self.scope_G, self.scope_B = data["scope_color"]
            self.scope_color_tolerance = data["scope_color_tolerance"]
            self.scope_R_alt, self.scope_G_alt, self.scope_B_alt = data["scope_color_alt"]
            self.scope_color_tolerance_alt = data["scope_color_tolerance_alt"]
        except KeyError as e:
            print(f"Missing key in config.json: {e}")
            exiting()

        # Initialize kmNet with the values from the config
        kmNet.init(self.ip, self.port, self.uid)

    def search_and_scope(self):
        sct = mss_module()
        while not self.exit_program:
            img = np.array(sct.grab(GRAB_ZONE))

            # Check for target color
            color_mask = (
                (img[:, :, 0] > self.R - self.color_tolerance) & (img[:, :, 0] < self.R + self.color_tolerance) &
                (img[:, :, 1] > self.G - self.color_tolerance) & (img[:, :, 1] < self.G + self.color_tolerance) &
                (img[:, :, 2] > self.B - self.color_tolerance) & (img[:, :, 2] < self.B + self.color_tolerance)
            )
            self.target_detected = np.any(color_mask)

            # Check for scope color
            scope_img = img[
                SCOPE_GRAB_ZONE["top"] - GRAB_ZONE["top"]:SCOPE_GRAB_ZONE["top"] - GRAB_ZONE["top"] + SCOPE_GRAB_ZONE["height"],
                SCOPE_GRAB_ZONE["left"] - GRAB_ZONE["left"]:SCOPE_GRAB_ZONE["left"] - GRAB_ZONE["left"] + SCOPE_GRAB_ZONE["width"]
            ]
            if kmNet.isdown_side2() == 1:
                scope_color = (self.scope_R_alt, self.scope_G_alt, self.scope_B_alt)
                scope_color_tolerance = self.scope_color_tolerance_alt
            else:
                scope_color = (self.scope_R, self.scope_G, self.scope_B)
                scope_color_tolerance = self.scope_color_tolerance

            scope_color_mask = (
                (scope_img[:, :, 0] > scope_color[0] - scope_color_tolerance) & (scope_img[:, :, 0] < scope_color[0] + scope_color_tolerance) &
                (scope_img[:, :, 1] > scope_color[1] - scope_color_tolerance) & (scope_img[:, :, 1] < scope_color[1] + scope_color_tolerance) &
                (scope_img[:, :, 2] > scope_color[2] - scope_color_tolerance) & (scope_img[:, :, 2] < scope_color[2] + scope_color_tolerance)
            )
            self.is_scoped = np.any(scope_color_mask)

            time.sleep(0.005)  # Reduced sleep interval for faster checking

    def trigger(self):
        while not self.exit_program:
            if self.is_scoped and self.target_detected:
                delay_percentage = self.trigger_delay / 100.0
                actual_delay = self.base_delay + self.base_delay * delay_percentage
                time.sleep(actual_delay)
                kmNet.enc_keydown(14)
                time.sleep(np.random.uniform(0.080, 0.12))
                kmNet.enc_keyup(14)
                time.sleep(np.random.uniform(0.05, 0.09))
            else:
                time.sleep(0.005)  # Reduced sleep interval for faster checking

    def starterino(self):
        threading.Thread(target=self.search_and_scope).start()
        threading.Thread(target=self.trigger).start()

if __name__ == "__main__":
    user32, kernel32, shcore = (
        WinDLL("user32", use_last_error=True),
        WinDLL("kernel32", use_last_error=True),
        WinDLL("shcore", use_last_error=True),
    )

    shcore.SetProcessDpiAwareness(2)
    WIDTH, HEIGHT = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    ZONE = 5
    GRAB_ZONE = {
        "left": int(WIDTH / 2 - ZONE),
        "top": int(HEIGHT / 2 - ZONE),
        "width": 2 * ZONE,
        "height": 2 * ZONE,
    }

    SCOPE_ZONE = 3  # Smaller zone for scoped detection
    SCOPE_GRAB_ZONE = {
        "left": int(WIDTH / 2 - SCOPE_ZONE),
        "top": int(HEIGHT / 2 - SCOPE_ZONE),
        "width": 2 * SCOPE_ZONE,
        "height": 2 * SCOPE_ZONE,
    }

    triggerbot_instance = TriggerBot()
    triggerbot_instance.starterino()
