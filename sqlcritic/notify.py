from abc import ABC, abstractmethod
from functools import cached_property
from typing import Iterator, List

from .analyze import AnalysisResult, AnalysisType
from .github import Pull


class Notifier(ABC):
    @abstractmethod
    def notify(self, report: Iterator[AnalysisResult]):
        raise NotImplementedError()


class GitHubNotifier(Notifier):
    def __init__(self, pull: Pull):
        self.pull = pull

    def notify(self, results: Iterator[AnalysisResult]):
        lines = self.format(results)
        self.pull.comment(lines)

    def format(self, results: Iterator[AnalysisResult]) -> List[str]:
        lines = []

        for result in results:
            if result.analysis_type == AnalysisType.N_PLUS_ONE:
                lines += [
                    "**Potential N+1 query detected**",
                    "```sql",
                    "--- source query",
                    result.queries[0],
                    "--- N query",
                    result.queries[1],
                    "```",
                    "Executed from:",
                ]
                for test in sorted(result.tests):
                    test_label = f"{test.path}::{test.name}"
                    lines.append(f"* `{test_label}` (line {test.line})")
            lines.append("---")

        if len(lines) == 0:
            lines = [
                "No issues detected!",
                "",
                "---",
            ]

        lines.append(
            "*Comment made by [sql-critic](https://github.com/scttnlsn/sql-critic)*"
        )

        return lines
