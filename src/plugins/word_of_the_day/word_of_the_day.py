from plugins.base_plugin.base_plugin import BasePlugin
import requests
import logging

logger = logging.getLogger(__name__)

WORDNIK_WOTD_URL = "https://api.wordnik.com/v4/words.json/wordOfTheDay?api_key={api_key}"


class WordOfTheDay(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['api_key'] = {
            "required": True,
            "service": "Wordnik",
            "expected_key": "WORDNIK_API_KEY"
        }
        template_params['style_settings'] = True
        return template_params

    def generate_image(self, settings, device_config):
        api_key = device_config.load_env_key("WORDNIK_API_KEY")
        if not api_key:
            raise RuntimeError("Wordnik API Key not configured.")

        try:
            word_data = self.fetch_word_of_the_day(api_key)
        except Exception as e:
            logger.error(f"Wordnik API request failed: {str(e)}")
            raise RuntimeError("Wordnik request failure, please check logs.")

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        template_params = {
            "word": word_data.get("word", ""),
            "part_of_speech": word_data.get("part_of_speech", ""),
            "definition": word_data.get("definition", ""),
            "example": word_data.get("example", ""),
            "note": word_data.get("note", ""),
            "plugin_settings": settings,
        }

        image = self.render_image(
            dimensions, "word_of_the_day.html", "word_of_the_day.css", template_params
        )

        if not image:
            raise RuntimeError("Failed to render image, please check logs.")
        return image

    def fetch_word_of_the_day(self, api_key):
        """Fetches the word of the day from the Wordnik API."""
        url = WORDNIK_WOTD_URL.format(api_key=api_key)
        response = requests.get(url)

        if not 200 <= response.status_code < 300:
            logger.error(f"Failed to fetch word of the day: {response.content}")
            raise RuntimeError("Failed to fetch word of the day from Wordnik.")

        data = response.json()
        word = data.get("word", "")

        # Extract the first definition
        definitions = data.get("definitions", [])
        definition = ""
        part_of_speech = ""
        if definitions:
            definition = definitions[0].get("text", "")
            part_of_speech = definitions[0].get("partOfSpeech", "")

        # Extract the first example, truncated for e-ink display
        examples = data.get("examples", [])
        example = ""
        if examples:
            example = examples[0].get("text", "")
            if len(example) > 180:
                example = example[:177].rsplit(" ", 1)[0] + "..."

        note = data.get("note", "")

        return {
            "word": word,
            "part_of_speech": part_of_speech,
            "definition": definition,
            "example": example,
            "note": note,
        }
