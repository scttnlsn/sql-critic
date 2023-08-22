import json
from unittest.mock import PropertyMock

from sqlcritic.action import Config, run
from sqlcritic.analyze import analyze
from sqlcritic.github import Pull
from sqlcritic.notify import GitHubNotifier
from sqlcritic.trace import parse_spans
from sqlcritic.utils import load_data


def mock_storage_get(key: str):
    if key == "test-base-sha/spans":
        return load_data("tests/fixtures/test-spans-base.json")
    elif key == "test-head-sha/spans":
        return load_data("tests/fixtures/test-spans.json")


def test_run(tmp_path, mocker):
    data = load_data("tests/fixtures/test-spans.json")

    data_path = tmp_path / "results.json"
    data_path.write_text(json.dumps(data))

    config = Config(
        data_path=str(data_path),
        repo_token="test-repo-token",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        aws_s3_bucket="test",
        event_name="push",
        repo="foo/bar",
        commit_sha="a03f0b090aecd9185310cf6200c1879085dc87cd",
        db_url="postgresql://postgres:postgres@localhost:5432/postgres",
    )
    mocker.patch(
        "sqlcritic.github.Repo.pulls",
        return_value=[
            Pull(None, 123),
        ],
    )
    mocker.patch(
        "sqlcritic.github.Pull.base_sha",
        return_value="test-base-sha",
        new_callable=PropertyMock,
    )
    mocker.patch(
        "sqlcritic.github.Pull.head_sha",
        return_value="test-head-sha",
        new_callable=PropertyMock,
    )

    storage_get = mocker.patch("sqlcritic.storage.Storage.get")
    storage_get.side_effect = mock_storage_get
    storage_put = mocker.patch("sqlcritic.storage.Storage.put")
    comment = mocker.patch("sqlcritic.github.Pull.comment")
    mocker.patch("sqlcritic.database.QueryExplainer.run", return_value={"test": "test"})

    run(config)

    notifier = GitHubNotifier(None)
    spans = parse_spans(data)
    results = analyze(spans)
    lines = notifier.format(results)

    storage_put.assert_any_call(f"{config.commit_sha}/spans", data)
    storage_put.assert_any_call(f"{config.commit_sha}/explain", {"test": "test"})
    comment.assert_called_once_with(lines)
