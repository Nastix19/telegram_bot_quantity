import requests

class RegosClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_items(self, limit=1000, offset=0):
        url = f"{self.base_url}/Item/Get"
        resp = requests.post(url, json={"limit": limit, "offset": offset})
        return resp.json().get("result", [])

    def get_stocks(self, limit=1000, offset=0):
        url = f"{self.base_url}/Stock/Get"
        resp = requests.post(url, json={"limit": limit, "offset": offset})
        return resp.json().get("result", [])

    def get_current_quantity(self, item_ids, stock_ids):
        if not stock_ids:
            raise ValueError("stock_ids обязателен")

        url = f"{self.base_url}/Item/GetCurrentQuantity"
        all_results = {}

        for i in range(0, len(item_ids), 250):
            batch = item_ids[i:i + 250]
            payload = {"item_ids": batch, "stock_ids": stock_ids}
            resp = requests.post(url, json=payload)
            results = resp.json().get("result", [])

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
