from typing import Any, Dict, List


def paginate(items: List[Dict[str, Any]], page: int, page_size: int = 5) -> List[Dict[str, Any]]:
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]


