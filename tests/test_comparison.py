from sqlcritic.analyze import AnalysisResult, AnalysisType
from sqlcritic.comparison import Comparison
from sqlcritic.trace import Test
from sqlcritic.utils import load_data


class MockStorage:
    def __init__(self, data: dict):
        self.data = data

    def get(self, key: str) -> any:
        return self.data.get(key)


def test_new_analysis_results():
    storage = MockStorage(
        {
            "test-base-sha/spans": load_data("tests/fixtures/test-spans-base.json"),
            "test-head-sha/spans": load_data("tests/fixtures/test-spans.json"),
        }
    )

    comparison = Comparison(
        storage=storage,
        base_sha="test-base-sha",
        head_sha="test-head-sha",
    )

    results = comparison.new_analysis_results()
    assert list(results) == [
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


def test_new_analysis_results_same_spans():
    storage = MockStorage(
        {
            "test-base-sha/spans": load_data("tests/fixtures/test-spans.json"),
            "test-head-sha/spans": load_data("tests/fixtures/test-spans.json"),
        }
    )

    comparison = Comparison(
        storage=storage,
        base_sha="test-base-sha",
        head_sha="test-head-sha",
    )

    results = comparison.new_analysis_results()
    # empty since there are no new results in the head
    assert list(results) == []
