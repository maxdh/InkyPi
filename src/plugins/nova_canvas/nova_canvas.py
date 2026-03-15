from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
from io import BytesIO
import boto3
import json
import base64
import random
import logging

logger = logging.getLogger(__name__)

MODEL_ID = "amazon.nova-canvas-v1:0"
DEFAULT_QUALITY = "standard"

# Nova Canvas supported sizes (width must be between 320-4096, height 320-4096)
# Total pixels must not exceed 4,194,304
ORIENTATIONS = {
    "horizontal": (1280, 720),
    "vertical": (720, 1280),
}


class NovaCanvas(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['api_key'] = {
            "required": True,
            "service": "AWS Bedrock (Nova Canvas)",
            "expected_key": "AWS_NOVA_ACCESS_KEY_ID"
        }
        return template_params

    def generate_image(self, settings, device_config):
        access_key = device_config.load_env_key("AWS_NOVA_ACCESS_KEY_ID")
        secret_key = device_config.load_env_key("AWS_NOVA_SECRET_ACCESS_KEY")
        region = device_config.load_env_key("AWS_NOVA_REGION") or "us-east-1"

        if not access_key or not secret_key:
            raise RuntimeError("AWS credentials for Nova Canvas not configured.")

        text_prompt = settings.get("textPrompt", "")
        if not text_prompt.strip():
            raise RuntimeError("Text Prompt is required.")

        orientation = device_config.get_config("orientation", default="horizontal")
        width, height = ORIENTATIONS.get(orientation, ORIENTATIONS["horizontal"])

        try:
            image = self.fetch_image(
                access_key, secret_key, region,
                text_prompt, width, height
            )
        except Exception as e:
            logger.error(f"Nova Canvas request failed: {str(e)}")
            raise RuntimeError(f"Nova Canvas request failure: {str(e)}")

        return image

    @staticmethod
    def fetch_image(access_key, secret_key, region, prompt, width, height):
        """Invoke Amazon Nova Canvas via Bedrock Runtime to generate an image."""
        logger.info(f"Generating Nova Canvas image: {prompt}, {width}x{height}")

        prompt += (
            ". The image should fully occupy the entire canvas without any frames, "
            "borders, or cropped areas. No blank spaces or artificial framing."
        )

        client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

        seed = random.randint(0, 858993459)

        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": prompt},
            "imageGenerationConfig": {
                "seed": seed,
                "quality": DEFAULT_QUALITY,
                "width": width,
                "height": height,
                "numberOfImages": 1,
            },
        }

        response = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body),
        )

        response_body = json.loads(response["body"].read())
        base64_image = response_body["images"][0]
        image_bytes = base64.b64decode(base64_image)

        return Image.open(BytesIO(image_bytes))
