from sqlcritic.collector import Collector


def test_collector():
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

    assert len(results) == 4
    result = results[0]
    assert result["name"] == "fake_db_span_1"
    assert result["attributes"]["db.name"] == "example"
    assert result["attributes"]["db.statement"] == "select * from foo;"
    result = results[1]
    assert result["name"] == "fake_db_span_2"
    assert result["attributes"]["db.name"] == "example"
    assert result["attributes"]["db.statement"] == "select * from bar;"
    result = results[2]
    assert result["name"] == "some_intermediate_span"
    result = results[3]
    assert result["name"] == "test"
    assert result["attributes"]["test.path"] == "example.py"
    assert result["attributes"]["test.line"] == 123
    assert result["attributes"]["test.name"] == "test_example"
