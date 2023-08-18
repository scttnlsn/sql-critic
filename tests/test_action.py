from sqlcritic.action import Config, run
from sqlcritic.analyze import analyze_path
from sqlcritic.notify import GitHubNotifier


def test_run(tmp_path, mocker):
    with open("tests/fixtures/test-spans.json") as f:
        data = f.read()
    data_path = tmp_path / "results.json"
    data_path.write_text(data)

    config = Config(
        data_path=str(data_path),
        repo_token="test-repo-token",
        event_name="pull_request",
        sha="a03f0b090aecd9185310cf6200c1879085dc87cd",
        ref="refs/pull/1/merge",
        repo="foo/bar",
    )

    comment = mocker.patch("sqlcritic.notify.GitHubNotifier.comment")

    run(config)

    notifier = GitHubNotifier(config.repo, 1, "test-repo-token")
    results = analyze_path(str(data_path))
    lines = notifier.format(results)

    comment.assert_called_once_with(lines)


def test_run_no_pull(tmp_path, mocker):
    config = Config(
        data_path="test-data-path.json",
        repo_token="test-repo-token",
        event_name="push",
        sha="a03f0b090aecd9185310cf6200c1879085dc87cd",
        ref="refs/heads/branchname",
        repo="foo/bar",
    )

    comment = mocker.patch("sqlcritic.notify.GitHubNotifier.comment")

    run(config)

    assert not comment.called
