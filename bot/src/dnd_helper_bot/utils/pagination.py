from typing import Any, Dict, List


# Default page size is intentionally kept at 5 for legacy callers (e.g., search flow).
# Lists (monsters/spells) should explicitly pass PAGE_SIZE_LIST.
PAGE_SIZE_LIST: int = 8


def paginate(items: List[Dict[str, Any]], page: int, page_size: int = 5) -> List[Dict[str, Any]]:
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]


