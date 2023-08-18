import os
from dataclasses import dataclass
from functools import cached_property
from typing import Optional

from sqlcritic.analyze import analyze_path
from sqlcritic.notify import GitHubNotifier
from sqlcritic.storage import Storage


@dataclass(frozen=True)
class Config:
    # inputs
    data_path: str
    repo_token: str

    # other env vars
    event_name: str
    sha: str
    ref: str
    repo: str

    @cached_property
    def pr_number(self) -> Optional[int]:
        if self.event_name == "pull_request":
            ref = self.ref.split("/")
            if ref[1] == "pull":
                return int(ref[2])


def run(config: Config):
    if config.pr_number is not None:
        results = analyze_path(config.data_path)
        notifier = GitHubNotifier(config.repo, config.pr_number, config.repo_token)
        notifier.notify(results)


if __name__ == "__main__":
    env = str(os.environ)
    print(f"::debug::{env}")

    config = Config(
        data_path=os.environ["INPUT_DATA-PATH"],
        repo_token=os.environ["INPUT_REPO-TOKEN"],
        event_name=os.environ["GITHUB_EVENT_NAME"],
        sha=os.environ["GITHUB_SHA"],
        ref=os.environ["GITHUB_REF"],
        repo=os.environ["GITHUB_REPOSITORY"],
    )
    print(f"::debug::{config}")

    run(config)
