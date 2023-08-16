from abc import ABC, abstractmethod
from functools import cached_property
from typing import Iterator, List

from github import Auth, Github
from github.Issue import Issue
from github.Repository import Repository

from .analyze import TestReport


class Notifier(ABC):
    @abstractmethod
    def notify(self, report: Iterator[TestReport]):
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

    def notify(self, report: Iterator[TestReport]):
        comment_lines = self._format_comment(report)
        self._leave_comment(comment_lines)

    def _leave_comment(self, lines: List[str]):
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

    def _format_comment(self, report: Iterator[TestReport]) -> List[str]:
        lines = []

        for test_report in report:
            test_label = f"{test_report.test.path}::{test_report.test.name}"
            # TODO: link label to file at this commit
            lines.append(f"* `{test_label}` (line {test_report.test.line})")
            for analysis_result in test_report.analysis_results:
                lines.append(
                    f"  - {analysis_result.message}: `{analysis_result.query}`"
                )

        if len(lines) == 0:
            lines = ["No issues detected!"]

        return lines
