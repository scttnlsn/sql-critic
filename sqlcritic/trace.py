from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dateutil import parser as dateparser


class SpanType(Enum):
    DB = "DB"
    TEST = "TEST"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, order=True)
class Test:
    __test__ = False

    path: str
    line: int
    name: str


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str
    attributes: Dict[str, Any]
    start_time: datetime
    end_time: datetime

    @classmethod
    def parse(cls, data: dict) -> "Span":
        return Span(
            name=data["name"],
            trace_id=data["context"]["trace_id"],
            span_id=data["context"]["span_id"],
            parent_id=data["parent_id"],
            attributes=data["attributes"],
            start_time=dateparser.parse(data["start_time"]),
            end_time=dateparser.parse(data["end_time"]),
        )

    def __hash__(self):
        return hash((self.name, self.trace_id, self.span_id, self.parent_id))

    @property
    def span_type(self) -> SpanType:
        if "db.statement" in self.attributes:
            return SpanType.DB
        elif "test.name" in self.attributes:
            return SpanType.TEST
        else:
            return SpanType.UNKNOWN

    @property
    def sql(self) -> Optional[str]:
        """
        Returns the query SQL if this span is of type `DB`
        """
        if self.span_type == SpanType.DB:
            sql = self.attributes["db.statement"]
            assert isinstance(sql, str)
            return sql
        return None

    @property
    def test(self) -> Optional[Test]:
        """
        Returns the test info if this span is of type `TEST`
        """
        if self.span_type == SpanType.TEST:
            return Test(
                path=self.attributes["test.path"],
                line=self.attributes["test.line"],
                name=self.attributes["test.name"],
            )
        return None


class Spans:
    def __init__(self, spans: List[Span]):
        self.spans = set(spans)
        self.index = {span.span_id: span for span in self.spans}

    def __iter__(self):
        yield from sorted(self.spans, key=lambda span: span.start_time)

    def parent_span(self, span: Span) -> Optional[Span]:
        """
        Returns the parent of the given span.
        """
        if span.parent_id is not None:
            return self.index[span.parent_id]

    def ancestors(self, span: Span) -> List[Span]:
        """
        Returns all ancestors of the given span in order (child comes after parent)
        """
        ancestors = []
        parent = self.parent_span(span)
        while parent is not None:
            ancestors.append(parent)
            parent = self.parent_span(parent)
        return ancestors


def parse_spans(data: List[dict]) -> Spans:
    return Spans([Span.parse(item) for item in data])
