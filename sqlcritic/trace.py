import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from dateutil import parser as dateparser


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str
    attributes: Dict[str, any]
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


class Spans:
    def __init__(self, spans: Iterator[Span]):
        self.spans = set(spans)
        self.index = {span.span_id: span for span in self.spans}

    def __iter__(self):
        yield from self.spans

    def parent_span(self, span: Span) -> Optional[Span]:
        if span.parent_id is not None:
            return self.index[span.parent_id]


@dataclass(frozen=True, order=True)
class Test:
    __test__ = False

    path: str
    line: int
    name: str


def load_data(path: str) -> List[dict]:
    with open(path) as f:
        return json.load(f)


def parse_spans(data: List[dict]) -> Spans:
    return Spans([Span.parse(item) for item in data])
