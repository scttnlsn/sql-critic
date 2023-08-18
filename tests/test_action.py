import json

from sqlcritic.action import Config, run
from sqlcritic.analyze import analyze
from sqlcritic.notify import GitHubNotifier
from sqlcritic.trace import load_data, parse_spans


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
        event_name="pull_request",
        sha="a03f0b090aecd9185310cf6200c1879085dc87cd",
        ref="refs/pull/1/merge",
        repo="foo/bar",
    )

    comment = mocker.patch("sqlcritic.notify.GitHubNotifier.comment")
    storage_put = mocker.patch("sqlcritic.storage.Storage.put")

    run(config)

    notifier = GitHubNotifier(config.repo, 1, "test-repo-token")
    spans = parse_spans(data)
    results = analyze(spans)
    lines = notifier.format(results)

    comment.assert_called_once_with(lines)
    storage_put.assert_called_once_with(config.sha, data)


def test_run_no_pull(tmp_path, mocker):
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
        sha="a03f0b090aecd9185310cf6200c1879085dc87cd",
        ref="refs/heads/branchname",
        repo="foo/bar",
    )

    comment = mocker.patch("sqlcritic.notify.GitHubNotifier.comment")
    storage_put = mocker.patch("sqlcritic.storage.Storage.put")

    run(config)

    assert not comment.called
    storage_put.assert_called_once_with(config.sha, data)
