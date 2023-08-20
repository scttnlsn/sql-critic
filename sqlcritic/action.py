import json
import os
from dataclasses import dataclass
from functools import cached_property
from typing import Optional

from sqlcritic.comparison import Commparison
from sqlcritic.github import Pull
from sqlcritic.notify import GitHubNotifier
from sqlcritic.storage import Storage
from sqlcritic.trace import load_data


@dataclass(frozen=True)
class Config:
    # inputs
    data_path: str
    repo_token: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_s3_bucket: str

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
    data = load_data(config.data_path)

    storage = Storage(
        access_key_id=config.aws_access_key_id,
        secret_access_key=config.aws_secret_access_key,
        bucket=config.aws_s3_bucket,
    )
    storage.put(config.sha, data)

    if config.pr_number is not None:
        pull = Pull(config.repo, config.repo_token, config.pr_number)

        comparison = Commparison(
            storage=storage,
            base_key=pull.base_sha,
            head_key=pull.head_sha,
            # TODO: maybe just pass in `data` here so we don't have to refetch the head data
        )

        notifier = GitHubNotifier(pull)
        notifier.notify(comparison.new_analysis_results())


if __name__ == "__main__":
    env = str(os.environ)
    print(f"::debug::{env}")

    config = Config(
        data_path=os.environ["INPUT_DATA-PATH"],
        repo_token=os.environ["INPUT_REPO-TOKEN"],
        aws_access_key_id=os.environ["INPUT_AWS-ACCESS-KEY-ID"],
        aws_secret_access_key=os.environ["INPUT_AWS-SECRET-ACCESS-KEY"],
        aws_s3_bucket=os.environ["INPUT_AWS-S3-BUCKET"],
        event_name=os.environ["GITHUB_EVENT_NAME"],
        sha=os.environ["GITHUB_SHA"],
        ref=os.environ["GITHUB_REF"],
        repo=os.environ["GITHUB_REPOSITORY"],
    )
    print(f"::debug::{config}")

    run(config)
