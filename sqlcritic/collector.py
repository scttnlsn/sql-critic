import json
import os
import os.path as path
import traceback
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from functools import cached_property
from typing import Iterator, List, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import Span, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class SpanProcessor(SimpleSpanProcessor):
    def on_start(self, span: Span, **kwargs):
        # was thinking we could use the stack trace to distinguish between
        # application code and test code but it's not always obious - i.e.
        # what if a test calls some application helper to create a bunch of fixtures?
        # that would look like queries from app code but isn't really
        stack = traceback.extract_stack()

        span.set_attribute(
            "stack",
            json.dumps(
                [
                    {
                        "path": frame.filename,
                        "line": frame.lineno,
                        "name": frame.name,
                    }
                    for frame in stack
                ]
            ),
        )


class Spans:
    def __init__(self, spans: Iterator[Span]):
        self.spans = set(spans)

    @cached_property
    def root_spans(self):
        return set(span for span in self.spans if span.parent is None)

    @cached_property
    def child_mapping(self):
        spans = set(self.spans)

        children = {}

        def traverse(parent_spans):
            nonlocal spans
            for parent_span in parent_spans:
                children[parent_span] = []
                for span in spans:
                    if span.parent == parent_span.get_span_context():
                        children[parent_span].append(span)
                traverse(children[parent_span])

        traverse(self.root_spans)
        return children

    def span_children(self, span):
        return sorted(
            self.child_mapping[span],
            key=lambda span: span.start_time,
        )

    def span_descendents(self, span):
        spans = []
        for child_span in self.span_children(span):
            spans.append(child_span)
            spans += self.span_children(child_span)
        return sorted(spans, key=lambda span: span.start_time)


@dataclass
class StackFrame:
    path: str
    line: int
    name: str

    def __post_init__(self):
        self.path = path.relpath(self.path)


@dataclass
class StackTrace:
    frames: List[StackFrame]

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["StackTrace"]:
        if data is None:
            return None
        return cls(frames=[StackFrame(**frame) for frame in data["frames"]])


@dataclass
class Query:
    sql: str
    stack_trace: Optional[StackTrace]

    @classmethod
    def from_dict(cls, data: dict) -> "Query":
        return cls(
            sql=data["sql"],
            stack_trace=StackTrace.from_dict(data.get("stack_trace")),
        )


@dataclass
class Test:
    __test__ = False

    path: str
    line: int
    name: str
    queries: List[Query]

    @classmethod
    def from_dict(cls, data: dict) -> "Test":
        return cls(
            path=data["path"],
            line=data["line"],
            name=data["name"],
            queries=[Query.from_dict(query_data) for query_data in data["queries"]],
        )


class Collector:
    def __init__(self):
        self.exporter = InMemorySpanExporter()
        self.processor = SpanProcessor(self.exporter)

        self.provider = TracerProvider()
        self.provider.add_span_processor(self.processor)

        trace.set_tracer_provider(self.provider)
        self.tracer = trace.get_tracer("sqlcritic")

    @contextmanager
    def trace_test(self, path: str, line: int, name: str):
        cwd = os.getcwd()
        relpath = os.path.relpath(path, cwd)

        with self.tracer.start_as_current_span("test") as span:
            span.set_attribute("test.path", relpath)
            span.set_attribute("test.name", name)
            span.set_attribute("test.line", line)
            yield

    def finished_spans(self) -> Spans:
        return Spans(self.exporter.get_finished_spans())

    def results(self) -> Iterator[Test]:
        spans = self.finished_spans()
        test_spans = (span for span in spans.root_spans if span.name == "test")

        for test_span in test_spans:
            test_info = Test(
                path=test_span.attributes["test.path"],
                line=test_span.attributes["test.line"],
                name=test_span.attributes["test.name"],
                queries=[],
            )

            db_spans = (
                span
                for span in spans.span_descendents(test_span)
                if "db.name" in span.attributes
            )

            for db_span in db_spans:
                stack = db_span.attributes.get("stack")
                if stack is None:
                    continue

                test_info.queries.append(
                    Query(
                        sql=db_span.attributes["db.statement"],
                        stack_trace=StackTrace.from_dict(
                            {
                                "frames": json.loads(stack),
                            }
                        ),
                    )
                )

            yield test_info

    def save_results(self, output_path: str):
        serialized = [asdict(result) for result in self.results()]
        with open(output_path, "w") as f:
            json.dump({"results": serialized}, f, indent=4)
