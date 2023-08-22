from sqlcritic.analyze import AnalysisResult, AnalysisType
from sqlcritic.github import Pull
from sqlcritic.notify import GitHubNotifier
from sqlcritic.trace import Test


def test_github_notify(mocker):
    results = [
        AnalysisResult(
            analysis_type=AnalysisType.N_PLUS_ONE,
            queries=[
                'SELECT "demo_entry"."id", "demo_entry"."author_id", "demo_entry"."content", "demo_entry"."published_at" FROM "demo_entry" ORDER BY "demo_entry"."published_at" DESC',
                'SELECT "demo_author"."id", "demo_author"."name" FROM "demo_author" WHERE "demo_author"."id" = %s LIMIT 21',
            ],
            tests=set(
                [
                    Test(path="tests/test_entries.py", line=9, name="test_entries"),
                    Test(
                        path="tests/test_entries.py", line=30, name="test_entries_other"
                    ),
                ]
            ),
        )
    ]

    comment = mocker.patch("sqlcritic.github.Pull.comment")

    notifier = GitHubNotifier(Pull(None, 123))
    notifier.notify(results)

    comment.assert_called_once_with(
        [
            "**Potential N+1 query detected**",
            "```sql",
            "--- source query",
            results[0].queries[0],
            "--- N query",
            results[0].queries[1],
            "```",
            "Executed from:",
            "* `tests/test_entries.py::test_entries` (line 9)",
            "* `tests/test_entries.py::test_entries_other` (line 30)",
            "---",
            "*Comment made by [sql-critic](https://github.com/scttnlsn/sql-critic)*",
        ]
    )


def test_github_notify_empty(mocker):
    comment = mocker.patch("sqlcritic.github.Pull.comment")

    notifier = GitHubNotifier(Pull(None, 123))
    notifier.notify([])

    comment.assert_called_once_with(
        [
            "No issues detected!",
            "",
            "---",
            "*Comment made by [sql-critic](https://github.com/scttnlsn/sql-critic)*",
        ]
    )
