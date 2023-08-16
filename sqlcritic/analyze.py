from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import List

from sqlcritic.collector import Query, Test


@dataclass
class AnalysisResult:
    query: str
    message: str


@dataclass
class TestReport:
    __test__ = False

    test: Test
    analysis_results: Iterator[AnalysisResult]


class Analyzer(ABC):
    @abstractmethod
    def analyze(self, queries: List[str]) -> Iterator[AnalysisResult]:
        raise NotImplementedError()


class NPlusOneAnalyzer(Analyzer):
    def analyze(self, queries: List[Query]) -> Iterator[AnalysisResult]:
        last_query = None
        detected = False
        for info in queries:
            query = info.sql
            if query.lower().startswith("select"):
                if query == last_query:
                    detected = True
                elif detected:
                    detected = False
                    yield self._result(last_query)
            last_query = query

        if detected:
            yield self._result(last_query)

    def _result(self, query: str) -> AnalysisResult:
        return AnalysisResult(query=query, message="Potential N+1 detected")


analyzers = [
    NPlusOneAnalyzer,
]


def analyze(tests: Iterator[Test]) -> Iterator[TestReport]:
    for test in tests:
        analysis_results = [
            result
            for analyzer in analyzers
            for result in analyzer().analyze(test.queries)
        ]

        if len(analysis_results) > 0:
            yield TestReport(
                test=test,
                analysis_results=analysis_results,
            )
