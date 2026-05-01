import json

from ..config import STATE_FILE_PATH


def load_portal_token() -> str | None:
    """从保存的 state.json 中提取 portal.sufe.edu.cn 的 token 值。"""
    if not STATE_FILE_PATH.exists():
        return None
    try:
        with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        return None

    target_origin = "https://portal.sufe.edu.cn"
    for origin_entry in state.get("origins", []):
        if origin_entry.get("origin") == target_origin:
            for item in origin_entry.get("localStorage", []):
                if item.get("name") == "vuex":
                    try:
                        vuex_data = json.loads(item.get("value", "{}"))
                        return vuex_data.get("user", {}).get("token")
                    except json.JSONDecodeError:
                        pass
                    break
    return None
