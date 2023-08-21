from urllib.parse import urlparse

from sqlcritic.database.postgres import PostgresAdapter
from sqlcritic.trace import Spans
from sqlcritic.utils import fingerprint


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
            if "db.statement" in span.attributes and span.name == "SELECT":
                # this span is a `select` query
                sql = span.attributes["db.statement"]
                f = fingerprint(sql)
                if f not in results:
                    result = self.adapter.explain(sql)
                    if result:
                        results[f] = result

        self.adapter.close()
        return results
