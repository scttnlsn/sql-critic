# sql-critic

[![CI status](https://github.com/scttnlsn/sql-critic/actions/workflows/ci.yml/badge.svg)](https://github.com/scttnlsn/sql-critic/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/sqlcritic.svg)](https://pypi.org/project/sqlcritic/)

Capture and analyze SQL queries made during a run of your app's test suite.

Receive feedback about dubious queries in a PR comment.

### How it works

#### Phase 1: Query collection

This phase hooks into your test suite and records any database queries captured
by [OpenTelementry](https://opentelemetry.io/) instrumentation.  If your database adapter
is not already instrumented then you will need to set that up as part of your test suite
initialization.

**NOTE**: This step only has Python language support at the moment!  However, it's a simple wrapper around OpenTelemetry which could be ported to any other language with OpenTelemetry support.

Example using `pytest` and `psycopg2`:

```python
# example conftest.py

from sqlcritic.collector import Collector

collector = Collector()

def pytest_sessionstart(session):
    # only necessary if your app is not already instrumented
    # Psycopg2 here is just an example - there is auto instrumentation for lots
    # of different database adapters
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    Psycopg2Instrumentor().instrument()

def pytest_runtest_call(item):
    path, line, name = item.reportinfo()

    with collector.trace_test(path, line, name):
        item.runtest()

def pytest_sessionfinish(session, exitstatus):
    collector.save_results("results.json")
```

#### Phase 2: Analysis

The analysis of queries collected during your test suite happens in a GitHub action.  Make sure to run this step after your test suite has run and outputted the queries results (i.e. in `results.json` for example).

```yaml
- uses: scttnlsn/sql-critic@main
  with:
    repo-token: ${{ secrets.GITHUB_TOKEN }}
    data-path: "results.json"

    # provide this if you'd like analyses based on explained query plans
    # (typically you'd connect to your test database after the test suite runs)
    db-url: "postgresql://postgres:postgres@localhost:5432/postgres"
```

The results will be posted as a PR comment in the repo utilizing this action.

### Analyses

* **N+1** - detects potential N+1 queries that can be common when using ORMs
* **Sequential scans** - detects queries that involve potential sequential scans over an entire table
  - this requires you provide a `db-url` input and preserve the schema in your test database after your test suite runs
  - TODO: need better heuristics here about which scans are acceptable vs. problematic

### Development

#### Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

#### Testing

```
docker-compose up -d # starts a Postgres service
python -m pytest
```

#### Dependencies

When dependencies are updated in `pyproject.toml` then we need to regenerate `requirements.txt`
(which is used for the GitHub action):

`pip-compile pyproject.toml`

#### Releasing

```
pip install build twine
make publish
```