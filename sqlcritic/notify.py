from abc import ABC, abstractmethod
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
                ] + self._source_lines(result)

            elif result.analysis_type == AnalysisType.SEQ_SCAN:
                lines += [
                    "**Potential sequential scan detected**",
                    "```sql",
                    result.queries[0],
                    "```",
                ] + self._source_lines(result)
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

    def _source_lines(self, result: AnalysisResult) -> List[str]:
        lines = ["Executed from:"]
        for test in sorted(result.tests):
            test_label = f"{test.path}::{test.name}"
            lines.append(f"* `{test_label}` (line {test.line})")
        return lines
