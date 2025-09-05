import threading
import time
import logging

try:
    import gpiod
    import gpiodevice
    from gpiod.line import Bias, Direction, Edge
except ImportError:
    gpiod = None
    gpiodevice = None

from refresh_task import ManualRefresh

logger = logging.getLogger(__name__)

class ButtonListener:
    """Polls Spectra 6 buttons and triggers manual comic refresh on SW_A press."""

    def __init__(self, refresh_task, device_config):
        self.refresh_task = refresh_task
        self.device_config = device_config
        self.thread = None
        self.running = False

    def start(self):
        if gpiod and gpiodevice:
            self.running = True
            self.thread = threading.Thread(target=self._poll_buttons, daemon=True)
            self.thread.start()
        else:
            logger.warning("gpiod/gpiodevice not available, button polling disabled.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _poll_buttons(self):
        # Raspberry Pi GPIO pins for Spectra 6 buttons
        BUTTONS = [5, 6, 16, 24]  # SW_A, SW_B, SW_C, SW_D
        LABELS = ["SW_A", "SW_B", "SW_C", "SW_D"]
        try:
            chip = gpiodevice.find_chip_by_platform()
            OFFSETS = [chip.line_offset_from_id(id) for id in BUTTONS]
            INPUT = gpiod.line.Request(direction=Direction.INPUT, edge_detection=Edge.FALLING, bias=Bias.PULL_UP)
            line_config = dict.fromkeys(OFFSETS, INPUT)
            request = chip.request_lines(consumer="spectra6-buttons", config=line_config)
        except Exception as e:
            logger.error(f"Failed to initialize button polling: {e}")
            return

        while self.running:
            for event in request.read_edge_events():
                index = OFFSETS.index(event.line_offset)
                label = LABELS[index]
                logger.info(f"Button press detected: {label}")
                if label == "SW_A":
                    # cf. blueprints/plugin.py:update_now
                    plugin_settings = {"comic": "XKCD"}  # Or load from config
                    refresh_action = ManualRefresh("comic", plugin_settings)
                    try:
                        self.refresh_task.manual_update(refresh_action)
                        logger.info("Manual comic refresh triggered by SW_A.")
                    except Exception as e:
                        logger.error(f"Error during manual comic refresh: {e}")
                elif label == "SW_B":
                    plugin_settings = {"comic": "Saturday Morning Breakfast Cereal"}  # Or load from config
                    refresh_action = ManualRefresh("comic", plugin_settings)
                    try:
                        self.refresh_task.manual_update(refresh_action)
                        logger.info("Manual comic refresh triggered by SW_B.")
                    except Exception as e:
                        logger.error(f"Error during manual comic refresh: {e}")
                elif label == "SW_C":
                    plugin_settings = {"comic": "Dinosaur Comics"}  # Or load from config
                    refresh_action = ManualRefresh("comic", plugin_settings)
                    try:
                        self.refresh_task.manual_update(refresh_action)
                        logger.info("Manual comic refresh triggered by SW_C.")
                    except Exception as e:
                        logger.error(f"Error during manual comic refresh: {e}")
                elif label == "SW_D":
                    plugin_settings = {"comic": "Cyanide & Happiness"}  # Or load from config
                    refresh_action = ManualRefresh("comic", plugin_settings)
                    try:
                        self.refresh_task.manual_update(refresh_action)
                        logger.info("Manual comic refresh triggered by SW_D.")
                    except Exception as e:
                        logger.error(f"Error during manual comic refresh: {e}")
            time.sleep(1)
