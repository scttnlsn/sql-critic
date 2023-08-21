from urllib.parse import urlparse

from sqlcritic.database.postgres import PostgresAdapter
from sqlcritic.trace import Spans, SpanType


class QueryExplainer:
    def __init__(self, db_url: str):
        self.db_url = db_url
        scheme = urlparse(self.db_url).scheme
        if scheme in ["postgres", "postgresql"]:
            self.adapter = PostgresAdapter(self.db_url)
        else:
            # TODO: support other database types
            raise NotImplementedError(f"unsupported database type: {scheme}")

    def run(self, spans: Spans) -> dict:
        results = {}

        self.adapter.connect()

        for span in spans:
            if span.span_type == SpanType.DB and span.name == "SELECT":
                descends_from_test = any(
                    [
                        ancestor.span_type == SpanType.TEST
                        for ancestor in spans.ancestors(span)
                    ]
                )
                if descends_from_test:
                    # this span is a `select` query executed from a test
                    sql = span.sql
                    if sql not in results:
                        result = self.adapter.explain(sql)
                        if result:
                            results[sql] = result

        self.adapter.close()
        return results
