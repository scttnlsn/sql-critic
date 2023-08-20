from functools import cached_property
from typing import List, Optional

from github import Auth, Github
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from github.Repository import Repository


class Pull:
    comment_marker = "<!--- comment made by sqlcritic --->"

    def __init__(self, repo_slug: str, token: str, number: int):
        self.repo_slug = repo_slug
        self.github = Github(auth=Auth.Token(token))
        self.number = number

    @cached_property
    def repo(self) -> Repository:
        return self.github.get_repo(self.repo_slug)

    @cached_property
    def pr(self) -> PullRequest:
        return self.repo.get_pull(self.number)

    @cached_property
    def issue(self) -> Issue:
        return self.repo.get_issue(self.number)

    @cached_property
    def base_sha(self) -> str:
        return self.pr.base.sha

    @cached_property
    def head_sha(self) -> str:
        return self.pr.head.sha

    def bot_comment(self) -> Optional[IssueComment]:
        # search for existing comment by this bot
        comments = self.issue.get_comments()

        for comment in comments:
            if self.comment_marker in comment.body:
                return comment

    def comment(self, lines: List[str]):
        content = "\n".join(lines)
        comment_body = f"{content}\n\n{self.comment_marker}"

        existing_comment = self.bot_comment()
        if existing_comment is not None:
            existing_comment.edit(comment_body)
        else:
            issue = self.repo.get_issue(self.number)
            issue.create_comment(comment_body)
