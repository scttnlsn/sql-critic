from sqlcritic.database import QueryExplainer


def test_postgres_explain(spans, db_url):
    query_explainer = QueryExplainer(db_url)
    results = query_explainer.run(spans)

    assert len(results) > 0
    for sql, plan in results.items():
        assert sql.strip().startswith("SELECT")
        assert "Plan" in plan  # output from Postgres explain
