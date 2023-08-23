import re
from typing import Optional

import psycopg2


class PostgresAdapter:
    def __init__(self, db_url: str):
        self.db_url = db_url

    def connect(self):
        self.connection = psycopg2.connect(self.db_url)

        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
            )
            res = cursor.fetchall()
            tables = [item[0] for item in res]
            print(f"::debug::tables={tables}")

    def close(self):
        if self.connection:
            self.connection.rollback()
            self.connection.close()
            self.connection = None

    def explain(self, query: str) -> Optional[dict]:
        try:
            with self.connection.cursor() as cursor:
                # Postgres might not use an index when there's not much (no) data
                cursor.execute("SET enable_seqscan = OFF;")

                # TODO: what if a different schema is being used?
                cursor.execute("SET search_path TO public;")

                # replace '%s' placeholders with '$N' where N=1..
                r = re.compile(r"\%s")
                n = len(r.findall(query))

                for i in range(1, n + 1):
                    query = query.replace("%s", f"${i}", 1)

                # find the number of parameters in the query
                r = re.compile(r"(\$\d+)")
                n = len(r.findall(query))

                # `unknown` type for each parameter
                args = ", ".join(["unknown"] * n)

                cursor.execute("SET plan_cache_mode = force_generic_plan;")

                statement = "stmt"
                if n > 0:
                    statement = f"stmt({args})"
                cursor.execute(f"PREPARE {statement} AS {query}")
                nulls = ", ".join(["NULL"] * n)
                if n > 0:
                    statement = f"stmt({nulls})"
                explain = f"EXPLAIN (FORMAT JSON) EXECUTE {statement}"
                cursor.execute(explain)
                (res,) = cursor.fetchone()
                cursor.execute("DEALLOCATE stmt;")

                return res[0]
        except psycopg2.errors.UndefinedTable:  # type: ignore
            return None
        finally:
            self.connection.rollback()


if __name__ == "__main__":
    import json
    import sys

    query = sys.argv[1]
    adapter = PostgresAdapter("postgresql://postgres:postres@localhost:5432/postgres")
    adapter.connect()
    res = adapter.explain(query)
    adapter.close()
    print(json.dumps(res))
