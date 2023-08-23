from functools import cached_property
from typing import Any, Iterator, Optional

from sqlcritic.analyze import AnalysisResult, analyze
from sqlcritic.storage import Storage
from sqlcritic.trace import parse_spans


class MissingBaseError(Exception):
    def __init__(self, sha):
        super().__init__("Missing base data")
        self.sha = sha


class MissingHeadError(Exception):
    def __init__(self, sha):
        super().__init__("Missing head data")
        self.sha = sha


class Comparison:
    def __init__(
        self,
        storage: Storage,
        base_sha: str,
        head_sha: str,
        head_span_data: Optional[Any] = None,
        head_explain_data: Optional[Any] = None,
    ):
        self.storage = storage
        self.base_sha = base_sha
        self.head_sha = head_sha
        self.head_span_data = head_span_data
        self.head_explain_data = head_explain_data

    @cached_property
    def base_results(self) -> Iterator[AnalysisResult]:
        span_data = self.storage.get(f"{self.base_sha}/spans")
        if span_data is None:
            raise MissingBaseError(self.base_sha)

        explain_data = self.storage.get(f"{self.base_sha}/explain")

        spans = parse_spans(span_data)
        return analyze(spans, explained=explain_data)

    @cached_property
    def head_results(self) -> Iterator[AnalysisResult]:
        span_data = self.head_span_data
        if span_data is None:
            span_data = self.storage.get(f"{self.head_sha}/spans")
        if span_data is None:
            raise MissingHeadError(self.head_sha)

        explain_data = self.head_explain_data
        if explain_data is None:
            explain_data = self.storage.get(f"{self.head_sha}/explain")

        spans = parse_spans(span_data)
        return analyze(spans, explained=explain_data)

    def new_analysis_results(self) -> Iterator[AnalysisResult]:
        """
        Returns analysis results that exist only in the head commit (and not in the base).
        """
        base_fingerprints = set([result.fingerprint for result in self.base_results])

        for result in self.head_results:
            if result.fingerprint not in base_fingerprints:
                yield result
