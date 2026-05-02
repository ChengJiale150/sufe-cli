import re
from datetime import datetime
from typing import cast

from bs4 import BeautifulSoup, NavigableString, Tag
from zoneinfo import ZoneInfo

from sufe_cli.errors import InvalidResponseError

from .client import sufe_get_canvas


def _extract_file_id(tag: Tag) -> str | None:
    """从 <a> 或 <img> 提取 Canvas 文件 ID

    优先级: data-api-endpoint > href > src
    匹配模式: /files/{id} 或 fileId={id}
    """
    for attr in ["data-api-endpoint", "href", "src"]:
        url = tag.get(attr)
        if url:
            match = re.search(r"/files/(\d+)", str(url))
            if match:
                return match.group(1)
            match = re.search(r"fileId=(\d+)", str(url))
            if match:
                return match.group(1)
    return None


def _convert_element(element) -> str:
    """递归转换 HTML 元素为 Markdown 文本"""
    if isinstance(element, NavigableString):
        return str(element)

    tag: Tag = element
    tag_name = tag.name

    # 递归转换子元素
    children_text = "".join(_convert_element(child) for child in tag.children)

    if tag_name in ("p", "div"):
        if children_text.strip():
            return children_text + "\n\n"
        return ""

    elif tag_name == "span":
        return children_text

    elif tag_name in ("strong", "b"):
        if children_text.strip():
            return f"**{children_text}**"
        return ""

    elif tag_name in ("em", "i"):
        if children_text.strip():
            return f"*{children_text}*"
        return ""

    elif tag_name == "br":
        return "\n"

    elif tag_name == "a":
        file_id = _extract_file_id(tag)
        if file_id:
            title = cast(str, tag.get("title", ""))
            display_text = title or children_text or "文件"
            return f"[{display_text}](file:{file_id})"
        else:
            href = cast(str, tag.get("href", ""))
            display_text = children_text or href
            return f"[{display_text}]({href})"

    elif tag_name == "img":
        alt = cast(str, tag.get("alt", ""))
        file_id = _extract_file_id(tag)
        if file_id:
            return f"[{alt}](file:{file_id})"
        else:
            src = cast(str, tag.get("src", ""))
            return f"![{alt}]({src})"

    elif tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag_name[1])
        if children_text.strip():
            return f"{'#' * level} {children_text}\n\n"
        return ""

    elif tag_name == "blockquote":
        if children_text.strip():
            lines = children_text.split("\n")
            quoted = "\n".join(f"> {line}" for line in lines)
            return quoted + "\n\n"
        return ""

    elif tag_name == "code":
        if children_text.strip():
            return f"`{children_text}`"
        return ""

    elif tag_name == "pre":
        if children_text.strip():
            return f"```\n{children_text}\n```\n\n"
        return ""

    elif tag_name == "ol":
        items = []
        for li in tag.find_all("li", recursive=False):
            li_text = "".join(_convert_element(child) for child in li.children).strip()
            if li_text:
                items.append(f"1. {li_text}")
        if items:
            return "\n".join(items) + "\n\n"
        return ""

    elif tag_name == "ul":
        items = []
        for li in tag.find_all("li", recursive=False):
            li_text = "".join(_convert_element(child) for child in li.children).strip()
            if li_text:
                items.append(f"- {li_text}")
        if items:
            return "\n".join(items) + "\n\n"
        return ""

    elif tag_name == "li":
        text = children_text.strip()
        if text:
            return f"- {text}\n"
        return ""

    elif tag_name in ("script", "style", "noscript"):
        return ""

    elif tag_name == "iframe":
        return str(tag)

    else:
        # 不支持的标签，保留原始 HTML
        return str(tag)


def html_to_markdown(html: str) -> str:
    """将 Canvas description HTML 转为 Markdown 文本"""
    if not html or not html.strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")

    parts = []
    for element in soup.children:
        if isinstance(element, NavigableString):
            text = str(element)
            if text.strip():
                parts.append(text)
        elif isinstance(element, Tag):
            parts.append(_convert_element(element))

    result = "".join(parts)

    # 清理连续空行（3+ 换行压缩为 2 个）
    result = re.sub(r"\n{3,}", "\n\n", result)
    # 清理首尾空白
    result = result.strip()

    return result


def utc_to_local(utc_str: str | None) -> str | None:
    """将 UTC 时间字符串转为东八区本地时间字符串"""
    if utc_str is None:
        return None
    dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    local_dt = dt.astimezone(ZoneInfo("Asia/Shanghai"))
    return local_dt.strftime("%Y-%m-%d %H:%M")


def has_next_page(response) -> bool:
    """检查 Canvas Link header 中是否有 rel=next 的分页链接"""
    link_header = response.headers.get("Link", "")
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return True
    return False


def fetch_all_pages(url: str, params: dict | None = None) -> list:
    """获取 Canvas API 所有分页数据"""
    all_data: list = []
    page = 1
    current_params = dict(params) if params else {}

    while True:
        current_params["page"] = page
        response = sufe_get_canvas(url, params=current_params)

        try:
            data = response.json()
        except Exception as e:
            raise InvalidResponseError(f"解析 JSON 失败: {e}") from e

        if not isinstance(data, list):
            raise InvalidResponseError("API 返回的数据格式异常，不是预期的列表格式。")

        all_data.extend(data)

        if not data or not has_next_page(response):
            break

        page += 1

    return all_data
