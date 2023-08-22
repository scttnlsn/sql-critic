import os
from dataclasses import dataclass
from functools import cached_property
from typing import Optional

from sqlcritic.comparison import Comparison
from sqlcritic.database import QueryExplainer
from sqlcritic.github import Pull
from sqlcritic.notify import GitHubNotifier
from sqlcritic.storage import Storage
from sqlcritic.trace import parse_spans
from sqlcritic.utils import current_git_sha, load_data


@dataclass(frozen=True)
class Config:
    # required inputs
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

    # optional inputs
    db_url: Optional[str] = None

    @cached_property
    def pr_number(self) -> Optional[int]:
        if self.event_name == "pull_request":
            ref = self.ref.split("/")
            if ref[1] == "pull":
                return int(ref[2])

    @cached_property
    def commit_sha(self) -> str:
        if self.pr_number is None:
            return self.sha
        else:
            return current_git_sha()


def run(config: Config):
    data = load_data(config.data_path)

    storage = Storage(
        access_key_id=config.aws_access_key_id,
        secret_access_key=config.aws_secret_access_key,
        bucket=config.aws_s3_bucket,
    )
    storage.put(f"{config.commit_sha}/spans", data)

    print(f"::debug::commit_sha={config.commit_sha}")

    if config.db_url:
        explainer = QueryExplainer(config.db_url)
        spans = parse_spans(data)
        results = explainer.run(spans)
        storage.put(f"{config.commit_sha}/explain", results)

    if config.pr_number is not None:
        pull = Pull(config.repo, config.repo_token, config.pr_number)

        head_data = None
        if config.commit_sha == pull.head_sha:
            head_data = data

        print(f"::debug::base_sha={pull.base_sha}")
        print(f"::debug::head_sha={pull.head_sha}")

        comparison = Comparison(
            storage=storage,
            base_sha=pull.base_sha,
            head_sha=pull.head_sha,
            head_span_data=head_data,
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
        db_url=os.environ.get("INPUT_DB-URL"),
    )

    print(f"::debug::{config}")

    run(config)
