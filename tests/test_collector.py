from sqlcritic.collector import Collector, Query, StackTrace, Test


def test_collect_queries():
    collector = Collector()

    with collector.trace_test("example.py", 123, "test_example"):
        with collector.tracer.start_as_current_span("fake_db_span_1") as span:
            span.set_attribute("db.name", "example")
            span.set_attribute("db.statement", "select * from foo;")
        with collector.tracer.start_as_current_span("some_intermediate_span") as span:
            with collector.tracer.start_as_current_span("fake_db_span_2") as span:
                span.set_attribute("db.name", "example")
                span.set_attribute("db.statement", "select * from bar;")

    results = list(collector.results())

    assert len(results) == 1
    test = results[0]
    assert test.path == "example.py"
    assert test.line == 123
    assert test.name == "test_example"
    assert len(test.queries) == 2
    query = test.queries[0]
    assert query.sql == "select * from foo;"
    assert query.stack_trace
    query = test.queries[1]
    assert query.sql == "select * from bar;"
    assert query.stack_trace
