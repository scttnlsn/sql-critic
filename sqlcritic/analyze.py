import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import List, Set

from sqlcritic.trace import Span, Spans, Test


def fingerprint(*items: List[str]) -> str:
    hashes = [hashlib.sha1(item.encode("utf-8")).hexdigest() for item in items]
    combined = "-".join(hashes)
    return hashlib.sha1(combined.encode("utf-8")).hexdigest()


class AnalysisType(Enum):
    N_PLUS_ONE = "N_PLUS_ONE"


@dataclass
class AnalysisResult:
    analysis_type: AnalysisType
    # list of relevant queries (context depends on analysis type)
    queries: List[str]
    # the set of tests which lead to this result
    tests: Set[Test]

    @property
    def fingerprint(self):
        return fingerprint(self.analysis_type.value, *self.queries)


class Analyzer(ABC):
    def __init__(self, spans: Spans):
        self.spans = spans
        self.results = {}

    def analyze(self) -> List[AnalysisResult]:
        spans = sorted(self.spans, key=lambda span: span.start_time)
        for span in spans:
            self.visit(span)
        self.finish()
        return list(self.results.values())

    @abstractmethod
    def visit(self, span: Span):
        pass

    def finish(self):
        pass


class NPlusOneAnalyzer(Analyzer):
    def __init__(self, spans: Spans):
        super().__init__(spans)
        self._source_span = None
        self._source_sql = None
        self._n_spans = []
        self._n_sql = None
        self.results = {}

    def visit(self, span: Span):
        if (
            "db.statement" in span.attributes
            and span.name == "SELECT"
            and span.parent_id is not None
        ):
            # this is a db query span
            sql = span.attributes["db.statement"]

            if self._source_span is None:
                # searching for the N+1 - maybe this span is the source that triggered it
                self._reset(span)
                return

            if span.parent_id != self._source_span.parent_id:
                # we have a new parent now, reset the detection
                self._reset(span)
                return

            if sql == self._source_sql:
                self._reset(span)
                return

            if self._n_sql is None or sql == self._n_sql:
                # we have a potential source and this is now a different query
                # with the same parent - maybe there's N of them
                self._n_sql = sql
                self._n_spans.append(span)
                return

            self._reset(span)

    def finish(self):
        if len(self._n_spans) > 1:
            self._save_result()

    def _fingerprint(self):
        return fingerprint(self._source_sql, self._n_sql)

    def _reset(self, span: Span):
        if len(self._n_spans) > 1:
            self._save_result()
        self._source_span = span
        self._source_sql = span.attributes["db.statement"]
        self._n_spans = []
        self._n_sql = None

    def _test_info(self, span: Span) -> Test:
        parent_span = None
        while True:
            parent_span = self.spans.parent_span(span)
            if parent_span is None:
                # we've traversed to the root span
                raise ValueError("span did not originate from a test")

            if "test.name" in parent_span.attributes:
                return Test(
                    path=parent_span.attributes["test.path"],
                    line=parent_span.attributes["test.line"],
                    name=parent_span.attributes["test.name"],
                )

            span = parent_span

    def _save_result(self):
        fingerprint = self._fingerprint()
        if fingerprint not in self.results:
            self.results[fingerprint] = AnalysisResult(
                analysis_type=AnalysisType.N_PLUS_ONE,
                queries=[self._source_sql, self._n_sql],
                tests=set(),
            )
        self.results[fingerprint].tests.add(self._test_info(self._source_span))


analyzers = [
    NPlusOneAnalyzer,
]


def analyze(spans: Spans) -> Iterator[AnalysisResult]:
    for analyzer in analyzers:
        yield from analyzer(spans).analyze()
