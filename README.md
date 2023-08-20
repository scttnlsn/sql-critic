# sql-critic

![CI status](https://github.com/scttnlsn/sql-critic/actions/workflows/ci.yml/badge.svg)

Capture and analyze SQL queries made during a run of your app's test suite.

Receive feedback about dubious queries in a PR comment.

### How it works

#### Phase 1: Query collection

This phase hooks into your test suite and records any database queries captured
by [OpenTelementry](https://opentelemetry.io/) instrumentation.

**NOTE**: This step only has Python language support at the moment!  However, it's a simple wrapper around OpenTelemetry which could be ported to any other language in theory.

Example using `pytest`:

```python
from sqlcritic.collector import Collector


collector = Collector()

def pytest_sessionstart(session):
    # only necessary if your app is not already instrumented
    # SQLite here is just an example - there is auto instrumentation for lots
    # of different database adapters
    from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
    SQLite3Instrumentor().instrument()

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
```

The results will be posted as a PR comment in the repo utilizing this action.

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
python -m pytest
```

#### Dependencies

When dependencies are updated in `pyproject.toml` then we need to regenerate `requirements.txt`
(which is used for the GitHub action):

`pip-compile -o requirements.txt pyproject.toml`

#### Releasing

```
pip install build twine
make publish
```