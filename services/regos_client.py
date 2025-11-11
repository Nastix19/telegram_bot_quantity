# services/regos_client.py
import requests
from typing import List, Dict, Optional

class RegosClient:
    """
    Простой синхронный клиент для вызовов REGOS API.
    base_url должен выглядеть как:
      https://integration.regos.uz/gateway/out/{connected_integration_id}/v1
    """
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, json_body: dict):
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = requests.post(url, json=json_body, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json().get("result", [])

    def get_items(self, limit: int = 1000, offset: int = 0) -> List[Dict]:
        return self._post("Item/Get", {"limit": limit, "offset": offset})

    def get_stocks(self, limit: int = 1000, offset: int = 0) -> List[Dict]:
        return self._post("Stock/Get", {"limit": limit, "offset": offset})

    def get_current_quantity(self, item_ids: List[int], stock_ids: List[int]) -> Dict[int, Dict[int, float]]:
        if not stock_ids:
            raise ValueError("stock_ids обязателен")
        # API может принимать большие массивы — отправляем пакетами по 250
        all_results: Dict[int, Dict[int, float]] = {}
        for i in range(0, len(item_ids), 250):
            batch = item_ids[i:i + 250]
            payload = {"item_ids": batch, "stock_ids": stock_ids}
            results = self._post("Item/GetCurrentQuantity", payload)
            for q in results:
                if not isinstance(q, dict):
                    continue
                item_id = q.get("item_id")
                stock_id = q.get("stock_id")
                quantity = q.get("quantity")
                if item_id is None or stock_id is None or quantity is None:
                    continue
                if item_id not in all_results:
                    all_results[item_id] = {}
                all_results[item_id][stock_id] = quantity
        return all_results
