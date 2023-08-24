from sqlcritic.database import DatabaseConnection
from sqlcritic.database.types import Index


def test_postgres_explain(spans, db_url):
    database = DatabaseConnection(db_url)
    results = database.explain(spans)

    assert len(results) > 0
    for sql, plan in results.items():
        assert sql.strip().startswith("SELECT")
        assert "Plan" in plan  # output from Postgres explain


def test_postgres_indexes(db_url):
    database = DatabaseConnection(db_url)
    results = database.indexes()

    assert set(results) == set(
        [
            Index(
                schema_name="public",
                table_name="demo_entry",
                index_name="demo_entry_pkey",
                columns=("id",),
            ),
            Index(
                schema_name="public",
                table_name="demo_entry",
                index_name="demo_entry_author_id_index",
                columns=("author_id",),
            ),
            Index(
                schema_name="public",
                table_name="demo_author",
                index_name="demo_author_pkey",
                columns=("id",),
            ),
        ]
    )
