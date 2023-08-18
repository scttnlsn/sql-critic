from abc import ABC, abstractmethod
from functools import cached_property
from typing import Iterator, List

from github import Auth, Github
from github.Issue import Issue
from github.Repository import Repository

from .analyze import AnalysisResult, AnalysisType


class Notifier(ABC):
    @abstractmethod
    def notify(self, report: Iterator[AnalysisResult]):
        raise NotImplementedError()


class GitHubNotifier(Notifier):
    """
    Leaves a PR comment with notification info.
    """

    comment_marker = "<!--- comment made by sqlcritic --->"

    def __init__(self, repo_slug: str, pr_number: int, token: str):
        self.repo_slug = repo_slug
        self.pr_number = pr_number
        self.token = token
        self.github = Github(auth=Auth.Token(self.token))

    @cached_property
    def repo(self) -> Repository:
        return self.github.get_repo(self.repo_slug)

    @cached_property
    def issue(self) -> Issue:
        # issue comments are not part of a review so fetch the PR as an issue
        # for use w/ commenting
        return self.repo.get_issue(self.pr_number)

    def notify(self, results: Iterator[AnalysisResult]):
        lines = self.format(results)
        self.comment(lines)

    def comment(self, lines: List[str]):
        content = "\n".join(lines)
        comment_body = f"{content}\n\n{self.comment_marker}"

        # search for existing comment by this bot
        comments = self.issue.get_comments()
        existing_comment = None
        for comment in comments:
            if self.comment_marker in comment.body:
                existing_comment = comment
                break

        if existing_comment is not None:
            existing_comment.edit(comment_body)
        else:
            self.issue.create_comment(comment_body)

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
                "---",
            ]

        lines.append(
            "*Comment made by [sql-critic](https://github.com/scttnlsn/sql-critic)*"
        )

        return lines
