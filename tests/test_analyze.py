import pytest

from sqlcritic.analyze import AnalysisResult, AnalysisType, analyze
from sqlcritic.trace import Test, load_data, parse_spans


@pytest.fixture
def spans():
    data = load_data("tests/fixtures/test-spans.json")
    return parse_spans(data)


def test_nplusone(spans):
    results = analyze(spans)

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
