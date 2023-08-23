from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

from sqlcritic.trace import Span, Spans, SpanType, Test
from sqlcritic.utils import fingerprint


class AnalysisType(Enum):
    N_PLUS_ONE = "N_PLUS_ONE"
    SEQ_SCAN = "SEQ_SCAN"


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
    def __init__(self, spans: Spans, explained: Optional[dict] = None):
        self.spans = spans
        self.explained = explained
        self.results: Dict[str, AnalysisResult] = {}

    def analyze(self) -> List[AnalysisResult]:
        for span in self.spans:
            self.visit(span)
        self.finish()
        return list(self.results.values())

    @abstractmethod
    def visit(self, span: Span):
        pass

    def finish(self):
        pass

    def test_info(self, span: Span) -> Optional[Test]:
        parent_span = None
        while True:
            parent_span = self.spans.parent_span(span)
            if parent_span is None:
                # we've traversed to the root span
                return None

            if parent_span.span_type == SpanType.TEST:
                return parent_span.test

            span = parent_span


class NPlusOneAnalyzer(Analyzer):
    def __init__(self, spans: Spans, explained: Optional[dict] = None):
        super().__init__(spans, explained=explained)
        self._source_span: Optional[Span] = None
        self._source_sql: Optional[str] = None
        self._n_spans: List[Span] = []
        self._n_sql: Optional[str] = None
        self.results = {}

    def visit(self, span: Span):
        if (
            span.span_type == SpanType.DB
            and span.name == "SELECT"
            and span.parent_id is not None
        ):
            # this is a db query span
            sql = span.sql

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
        self._source_sql = span.sql
        self._n_spans = []
        self._n_sql = None

    def _save_result(self):
        fingerprint = self._fingerprint()
        if fingerprint not in self.results:
            self.results[fingerprint] = AnalysisResult(
                analysis_type=AnalysisType.N_PLUS_ONE,
                queries=[self._source_sql, self._n_sql],
                tests=set(),
            )
        test = self.test_info(self._source_span)
        if test is not None:
            self.results[fingerprint].tests.add(test)


class SeqScanAnalyzer(Analyzer):
    # TODO: this is all very Postgres-specific
    # will need to abstract a lot of this when there are other plan formats

    def visit(self, span: Span):
        if self.explained is None:
            return

        if span.span_type == SpanType.DB and span.sql in self.explained:
            plan = self.explained[span.sql]["Plan"]
            if self._contains_seq_scan(plan):
                assert span.sql is not None
                f = fingerprint(span.sql)
                if f not in self.results:
                    self.results[f] = AnalysisResult(
                        analysis_type=AnalysisType.SEQ_SCAN,
                        queries=[span.sql],
                        tests=set(),
                    )
                test = self.test_info(span)
                if test is not None:
                    self.results[f].tests.add(test)

    def _contains_seq_scan(self, plan: dict) -> bool:
        if plan["Node Type"] == "Seq Scan":
            return True

        if "Plans" in plan:
            # has sub plans
            return any(
                [self._contains_seq_scan(sub_plan) for sub_plan in plan["Plans"]]
            )

        return False


analyzers = [
    NPlusOneAnalyzer,
    SeqScanAnalyzer,
]


def analyze(spans: Spans, explained: Optional[dict] = None) -> Iterator[AnalysisResult]:
    for analyzer in analyzers:
        yield from analyzer(spans, explained=explained).analyze()
