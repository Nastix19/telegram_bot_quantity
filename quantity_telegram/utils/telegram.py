def extract_chat_id(payload: dict):
    return (
        payload.get("message", {})
        .get("chat", {})
        .get("id")
        or payload.get("callback_query", {})
        .get("message", {})
        .get("chat", {})
        .get("id")
    )
