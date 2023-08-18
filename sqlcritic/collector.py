import json
import os
from contextlib import contextmanager
from typing import List

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class Collector:
    def __init__(self):
        self.exporter = InMemorySpanExporter()
        self.processor = SimpleSpanProcessor(self.exporter)

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

    def results(self) -> List[dict]:
        spans = self.exporter.get_finished_spans()
        data = [json.loads(span.to_json()) for span in spans]
        return data

    def save_results(self, output_path: str):
        with open(output_path, "w") as f:
            json.dump(self.results(), f)
