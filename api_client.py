import hashlib
from typing import Dict

import config


class FragmentAPIClient:
    """Payment API client — только для вебхуков и проверки Shop Key"""

    def __init__(self):
        self.shop_id = config.SHOP_ID
        self.shop_key = config.SHOP_KEY

    def verify_callback(self, data: Dict) -> bool:
        received_signature = data.get("signature", "")
        sign_string = f"{data.get('order_id')}:{data.get('amount')}:{self.shop_key}"
        expected_signature = hashlib.sha256(sign_string.encode()).hexdigest()
        return received_signature == expected_signature


api_client = FragmentAPIClient()
