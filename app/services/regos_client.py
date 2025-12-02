import httpx

class RegosClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_items(self):
        r = await self.client.post(f"{self.base_url}/Item/Get", json={"limit": 1000})
        return r.json().get("result", [])

    async def get_stocks(self):
        r = await self.client.post(f"{self.base_url}/Stock/Get", json={"limit": 1000})
        return r.json().get("result", [])

    async def get_current_quantity(self, item_ids: list[int], stock_ids: list[int]):
        results = {}
        for i in range(0, len(item_ids), 250):
            batch = item_ids[i:i+250]
            r = await self.client.post(
                f"{self.base_url}/Item/GetCurrentQuantity",
                json={"item_ids": batch, "stock_ids": stock_ids}
            )
            for e in r.json().get("result", []):
                item_id = e.get("item_id")
                stock_id = e.get("stock_id")
                qty = e.get("quantity")
                if item_id and stock_id and qty is not None:
                    results.setdefault(item_id, {})[stock_id] = qty
        return results

    async def close(self):
        await self.client.aclose()