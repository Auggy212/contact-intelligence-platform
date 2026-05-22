import math
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if page_size else 0,
    }


def offset_from_page(page: int, page_size: int) -> int:
    return (page - 1) * page_size
