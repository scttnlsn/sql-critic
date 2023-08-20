from functools import cached_property
from typing import Iterator

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


class Commparison:
    def __init__(self, storage: Storage, base_key: str, head_key: str):
        self.storage = storage
        self.base_key = base_key
        self.head_key = head_key

    @cached_property
    def base_results(self) -> Iterator[AnalysisResult]:
        data = self.storage.get(self.base_key)
        if data is None:
            raise MissingBaseError(self.base_key)

        spans = parse_spans(data)
        return analyze(spans)

    @cached_property
    def head_results(self) -> Iterator[AnalysisResult]:
        data = self.storage.get(self.head_key)
        if data is None:
            raise MissingHeadError(self.head_key)

        spans = parse_spans(data)
        return analyze(spans)

    def new_analysis_results(self) -> Iterator[AnalysisResult]:
        """
        Returns analysis results that exist only in the head commit (and not in the base).
        """
        base_fingerprints = set([result.fingerprint for result in self.base_results])

        for result in self.head_results:
            if result.fingerprint not in base_fingerprints:
                yield result
