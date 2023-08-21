from sqlcritic.database import QueryExplainer

db_url = "postgresql://postgres:postgres@localhost:5432/postgres"


def test_postgres_explain(spans):
    query_explainer = QueryExplainer(db_url)
    results = query_explainer.run(spans)

    assert len(results) > 0
    for sql, plan in results.items():
        print(sql)
        assert sql.strip().startswith("SELECT")
        assert "Plan" in plan  # output from Postgres explain
