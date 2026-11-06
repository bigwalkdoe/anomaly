from __future__ import annotations

import json
from typing import Any

from sqlalchemy import JSON as _SQLAlchemyJSON
from sqlalchemy.types import TypeDecorator


class JSONType(TypeDecorator[Any]):
    """JSON column type that serializes UUID/datetime (and other non-native
    values) to strings via ``json.dumps(..., default=str)``.

    SQLAlchemy's default JSON serializer calls ``json.dumps`` without a
    ``default`` callable, which raises ``TypeError`` for ``uuid.UUID`` and
    ``datetime`` objects.  This decorator pre-serializes the value so the
    underlying JSON column receives an already-encoded string, and decodes
    it back on read.
    """

    impl = _SQLAlchemyJSON
    cache_ok = True

    def bind_processor(self, dialect: Any) -> Any:
        def process(value: Any) -> Any:
            if value is _SQLAlchemyJSON.NULL:
                value = None
            if value is None:
                return None
            return json.dumps(value, default=str)

        return process

    def result_processor(self, dialect: Any, coltype: Any) -> Any:
        def process(value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, str):
                return json.loads(value)
            return value

        return process


# Convenience aliases for callers that expect different names.
AnomalyJSON = JSONType
UUIDJSON = JSONType
CustomJSON = JSONType
JSON = JSONType
