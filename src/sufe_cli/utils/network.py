from typing import Dict

def get_default_headers() -> Dict[str, str]:
    """返回通用的网络请求伪装头"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Referer": "https://lclibrary.sufe.edu.cn/ClientWeb/xcus/ic2/Default.aspx",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
