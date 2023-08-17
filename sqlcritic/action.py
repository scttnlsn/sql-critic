import json
import os

from sqlcritic.analyze import analyze
from sqlcritic.collector import Test
from sqlcritic.notify import GitHubNotifier
from sqlcritic.storage import Storage


def main():
    env = str(os.environ)
    print(f"::debug::{env}")

    data_path = os.environ["INPUT_DATA-PATH"]
    results_data = None
    with open(data_path) as f:
        results_data = json.loads(f.read())
    print(f"::debug::results_data={results_data}")

    current_sha = os.environ["GITHUB_SHA"]

    # storage = Storage(
    #     aws_access_key_id=os.environ["INPUT_AWS-ACCESS-KEY-ID"],
    #     aws_secret_access_key=os.environ["INPUT_AWS-SECRET-ACCESS-KEY"],
    #     bucket=os.environ["INPUT_AWS-S3-BUCKET"],
    # )
    # storage.put(current_sha, results_data)

    if os.environ["GITHUB_EVENT_NAME"] == "pull_request":
        ref = os.environ["GITHUB_REF"].split("/")
        if ref[1] != "pull":
            print("::debug::no pull")
            return

        pr_number = int(ref[2])
        repo_slug = os.environ["GITHUB_REPOSITORY"]
        token = os.environ["INPUT_REPO-TOKEN"]

        tests = [Test.from_dict(test_data) for test_data in results_data["results"]]
        report = analyze(tests)
        notifier = GitHubNotifier(repo_slug, pr_number, token)
        notifier.notify(report)


if __name__ == "__main__":
    main()
