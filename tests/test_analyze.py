from sqlcritic.analyze import (
    AnalysisResult,
    AnalysisType,
    MissingIndexAnalyzer,
    NPlusOneAnalyzer,
    SeqScanAnalyzer,
)
from sqlcritic.trace import Test


def test_nplusone(spans):
    results = NPlusOneAnalyzer(spans).analyze()

    assert list(results) == [
        AnalysisResult(
            analysis_type=AnalysisType.N_PLUS_ONE,
            queries=[
                'SELECT "demo_entry"."id", "demo_entry"."author_id", "demo_entry"."content", "demo_entry"."published_at" FROM "demo_entry" ORDER BY "demo_entry"."published_at" DESC',
                'SELECT "demo_author"."id", "demo_author"."name" FROM "demo_author" WHERE "demo_author"."id" = %s LIMIT 21',
            ],
            tests={
                Test(path="tests/test_entries.py", line=9, name="test_entries"),
                Test(path="tests/test_entries.py", line=30, name="test_entries_other"),
            },
        )
    ]


def test_seq_scan(spans, metadata):
    results = SeqScanAnalyzer(spans, metadata=metadata).analyze()

    assert list(results) == [
        AnalysisResult(
            analysis_type=AnalysisType.SEQ_SCAN,
            queries=[
                'SELECT "demo_entry"."id", "demo_entry"."author_id", "demo_entry"."content", "demo_entry"."published_at" FROM "demo_entry" ORDER BY "demo_entry"."published_at" DESC'
            ],
            tests={
                Test(path="tests/test_entries.py", line=9, name="test_entries"),
                Test(path="tests/test_entries.py", line=30, name="test_entries_other"),
            },
        )
    ]


def test_index(spans, metadata):
    metadata["indexes"] = [
        {
            "columns": ("author_id",),
            "index_name": "demo_entry_author_id_index",
            "schema_name": "public",
            "table_name": "demo_entry",
        },
        {
            "columns": ("id",),
            "index_name": "demo_entry_pkey",
            "schema_name": "public",
            "table_name": "demo_entry",
        },
    ]
    results = MissingIndexAnalyzer(spans, metadata=metadata).analyze()
    assert results == [
        AnalysisResult(
            analysis_type=AnalysisType.MISSING_INDEX,
            queries=[
                'SELECT "demo_author"."id", "demo_author"."name" FROM "demo_author" WHERE "demo_author"."id" = %s LIMIT 21'
            ],
            tests={
                Test(path="tests/test_entries.py", line=30, name="test_entries_other"),
                Test(path="tests/test_entries.py", line=9, name="test_entries"),
            },
            extra={"demo_author": ["id"]},
        )
    ]
