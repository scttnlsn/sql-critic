from sqlcritic.analyze import AnalysisResult, TestReport, analyze
from sqlcritic.collector import Test


def test_nplusone():
    data = {
        "results": [
            {
                "path": "tests/some_test.py",
                "line": 123,
                "name": "test_something",
                "queries": [
                    {"sql": "SELECT * FROM foo LIMIT 10", "stack_trace": None},
                    {"sql": "SELECT * FROM bar WHERE foo_id = ?", "stack_trace": None},
                    {"sql": "SELECT * FROM bar WHERE foo_id = ?", "stack_trace": None},
                    {"sql": "SELECT * FROM bar WHERE foo_id = ?", "stack_trace": None},
                    {"sql": "SELECT * FROM baz LIMIT 10", "stack_trace": None},
                    {"sql": "SELECT * FROM qux WHERE baz_id = ?", "stack_trace": None},
                    {"sql": "SELECT * FROM qux WHERE baz_id = ?", "stack_trace": None},
                    {"sql": "SELECT * FROM qux WHERE baz_id = ?", "stack_trace": None},
                ],
            }
        ]
    }

    tests = [Test.from_dict(test_data) for test_data in data["results"]]

    results = list(analyze(tests))

    assert results == [
        TestReport(
            test=tests[0],
            analysis_results=[
                AnalysisResult(
                    query="SELECT * FROM bar WHERE foo_id = ?",
                    message="Potential N+1 detected",
                ),
                AnalysisResult(
                    query="SELECT * FROM qux WHERE baz_id = ?",
                    message="Potential N+1 detected",
                ),
            ],
        ),
    ]
