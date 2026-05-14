from typing import Any, Optional

from fastapi import HTTPException


def ok(data: Any, meta: Optional[dict] = None) -> dict:
    return {"data": data, "error": None, "meta": meta or {}}


def paginated(data: Any, page: int, size: int, total: int) -> dict:
    return ok(data, {"page": page, "size": size, "total": total})


def err(code: str, message: str, status: int = 400) -> None:
    raise HTTPException(
        status_code=status,
        detail={"data": None, "error": {"code": code, "message": message}, "meta": {}},
    )
