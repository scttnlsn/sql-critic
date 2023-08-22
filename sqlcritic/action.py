import os
from dataclasses import dataclass
from typing import Optional

from sqlcritic.comparison import Comparison
from sqlcritic.database import QueryExplainer
from sqlcritic.github import Repo
from sqlcritic.notify import GitHubNotifier
from sqlcritic.storage import Storage
from sqlcritic.trace import parse_spans
from sqlcritic.utils import load_data


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
    commit_sha: str
    repo: str

    # optional inputs
    db_url: Optional[str] = None


def run(config: Config):
    data = load_data(config.data_path)

    storage = Storage(
        access_key_id=config.aws_access_key_id,
        secret_access_key=config.aws_secret_access_key,
        bucket=config.aws_s3_bucket,
    )
    storage.put(f"{config.commit_sha}/spans", data)

    if config.db_url:
        explainer = QueryExplainer(config.db_url)
        spans = parse_spans(data)
        results = explainer.run(spans)
        storage.put(f"{config.commit_sha}/explain", results)

    repo = Repo(config.repo, config.repo_token)

    for pull in repo.pulls(config.commit_sha):
        head_data = None
        if config.commit_sha == pull.head_sha:
            head_data = data

        print(f"::debug::pull={pull.number}")
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
        repo=os.environ["GITHUB_REPOSITORY"],
        commit_sha=os.environ["GITHUB_SHA"],
        db_url=os.environ.get("INPUT_DB-URL"),
    )

    print(f"::debug::{config}")

    if config.event_name == "push":
        run(config)
