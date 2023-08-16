from sqlcritic.analyze import AnalysisResult, TestReport
from sqlcritic.collector import Test
from sqlcritic.notify import GitHubNotifier


def test_github_notify(mocker):
    report = [
        TestReport(
            test=Test(
                path="tests/test_example.py",
                line=123,
                name="test_something",
                queries=[],
            ),
            analysis_results=[
                AnalysisResult(
                    query="SELECT * FROM foo",
                    message="Test message",
                )
            ],
        )
    ]

    leave_comment = mocker.patch("sqlcritic.notify.GitHubNotifier._leave_comment")

    notifier = GitHubNotifier("someowner/somerepo", 123, "faketoken")
    notifier.notify(report)

    leave_comment.assert_called_once_with(
        [
            "* `tests/test_example.py::test_something` (line 123)",
            "  - Test message: `SELECT * FROM foo`",
        ]
    )


def test_github_notify_empty(mocker):
    leave_comment = mocker.patch("sqlcritic.notify.GitHubNotifier._leave_comment")

    notifier = GitHubNotifier("someowner/somerepo", 123, "faketoken")
    notifier.notify([])

    leave_comment.assert_called_once_with(["No issues detected!"])
