from functools import cached_property
from typing import List, Optional

from github import Auth, Github
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.PullRequest import PullRequest
from github.Repository import Repository


class Pull:
    comment_marker = "<!--- comment made by sqlcritic --->"

    def __init__(self, repo: Repository, number: int):
        self.repo = repo
        self.number = number

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
        return None

    def comment(self, lines: List[str]):
        content = "\n".join(lines)
        comment_body = f"{content}\n\n{self.comment_marker}"

        existing_comment = self.bot_comment()
        if existing_comment is not None:
            existing_comment.edit(comment_body)
        else:
            issue = self.repo.get_issue(self.number)
            issue.create_comment(comment_body)


class Repo:
    def __init__(self, repo_slug: str, token: str):
        self.repo_slug = repo_slug
        self.github = Github(auth=Auth.Token(token))

    @cached_property
    def _repo(self):
        return self.github.get_repo(self.repo_slug)

    def pull(self, number: int) -> Pull:
        return Pull(self._repo, number)

    def pulls(self, commit_sha: str) -> List[Pull]:
        commit = self._repo.get_commit(commit_sha)
        return [self.pull(pull.number) for pull in commit.get_pulls()]
