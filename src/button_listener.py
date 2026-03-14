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
    """Polls Spectra 6 buttons and triggers configurable actions on button press."""

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

    def get_button_config(self):
        """Get button configuration from device config with fallback defaults."""
        button_config = self.device_config.get_config("button_config", {})
        
        # Fallback to default config if not configured
        if not button_config:
            logger.warning("No button configuration found, using defaults")
            button_config = {
                "SW_A": {
                    "action_type": "plugin_refresh",
                    "plugin_id": "comic",
                    "plugin_settings": {"comic": "XKCD"}
                },
                "SW_B": {
                    "action_type": "plugin_refresh", 
                    "plugin_id": "comic",
                    "plugin_settings": {"comic": "Saturday Morning Breakfast Cereal"}
                },
                "SW_C": {
                    "action_type": "plugin_refresh",
                    "plugin_id": "comic", 
                    "plugin_settings": {"comic": "Dinosaur Comics"}
                },
                "SW_D": {
                    "action_type": "plugin_refresh",
                    "plugin_id": "comic",
                    "plugin_settings": {"comic": "Cyanide & Happiness"}
                }
            }
        
        return button_config

    def execute_button_action(self, button_label, button_config):
        """Execute the configured action for a button press."""
        try:
            action_type = button_config.get("action_type", "plugin_refresh")
            
            if action_type == "plugin_refresh":
                plugin_id = button_config.get("plugin_id")
                plugin_settings = button_config.get("plugin_settings", {})
                
                if not plugin_id:
                    logger.error(f"No plugin_id configured for button {button_label}")
                    return
                
                # Verify plugin exists
                plugin_config = self.device_config.get_plugin(plugin_id)
                if not plugin_config:
                    logger.error(f"Plugin '{plugin_id}' not found for button {button_label}")
                    return
                
                refresh_action = ManualRefresh(plugin_id, plugin_settings)
                self.refresh_task.manual_update(refresh_action)
                logger.info(f"Manual refresh triggered by {button_label} for plugin '{plugin_id}'")
                
            else:
                logger.warning(f"Unknown action_type '{action_type}' for button {button_label}")
                
        except Exception as e:
            logger.error(f"Error executing action for button {button_label}: {e}")

    def _poll_buttons(self):
        # Raspberry Pi GPIO pins for Spectra 6 buttons
        BUTTONS = [5, 6, 16, 24]  # SW_A, SW_B, SW_C, SW_D
        LABELS = ["SW_A", "SW_B", "SW_C", "SW_D"]
        
        try:
            chip = gpiodevice.find_chip_by_platform()
            OFFSETS = [chip.line_offset_from_id(id) for id in BUTTONS]
            # Create settings for all the input pins, we want them to be inputs
            # with a pull-up and a falling edge detection.
            INPUT = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP, edge_detection=Edge.FALLING)
            line_config = dict.fromkeys(OFFSETS, INPUT)
            request = chip.request_lines(consumer="spectra6-buttons", config=line_config)
        except Exception as e:
            logger.error(f"Failed to initialize button polling: {e}")
            return

        # Get button configuration
        button_config = self.get_button_config()

        while self.running:
            for event in request.read_edge_events():
                index = OFFSETS.index(event.line_offset)
                label = LABELS[index]
                logger.info(f"Button press detected: {label}")
                
                # Get configuration for this button
                config = button_config.get(label)
                if config:
                    self.execute_button_action(label, config)
                else:
                    logger.warning(f"No configuration found for button {label}")
                    
            time.sleep(1)