import re
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type

from sqlglot import exp, parse_one

from sqlcritic.database.types import Index
from sqlcritic.trace import Span, Spans, SpanType, Test
from sqlcritic.utils import fingerprint


class AnalysisType(Enum):
    N_PLUS_ONE = "N_PLUS_ONE"
    SEQ_SCAN = "SEQ_SCAN"
    MISSING_INDEX = "MISSING_INDEX"


@dataclass
class AnalysisResult:
    analysis_type: AnalysisType
    # list of relevant queries (context depends on analysis type)
    queries: List[str]
    # the set of tests which lead to this result
    tests: Set[Test]
    # extra info
    extra: Optional[Dict[str, Any]] = None

    @property
    def fingerprint(self):
        return fingerprint(self.analysis_type.value, *self.queries)


class Analyzer(ABC):
    def __init__(self, spans: Spans, metadata: Optional[dict] = None):
        self.spans = spans
        self.metadata = metadata
        self.results: Dict[str, AnalysisResult] = {}

    def analyze(self) -> List[AnalysisResult]:
        for span in self.spans:
            self.visit(span)
        self.finish()
        return list(self.results.values())

    @abstractmethod
    def visit(self, span: Span):
        pass

    def finish(self):
        pass

    def test_info(self, span: Span) -> Optional[Test]:
        parent_span = None
        while True:
            parent_span = self.spans.parent_span(span)
            if parent_span is None:
                # we've traversed to the root span
                return None

            if parent_span.span_type == SpanType.TEST:
                return parent_span.test

            span = parent_span


class NPlusOneAnalyzer(Analyzer):
    def __init__(self, spans: Spans, metadata: Optional[dict] = None):
        super().__init__(spans, metadata=metadata)
        self._source_span: Optional[Span] = None
        self._source_sql: Optional[str] = None
        self._n_spans: List[Span] = []
        self._n_sql: Optional[str] = None
        self.results = {}

    def visit(self, span: Span):
        if (
            span.span_type == SpanType.DB
            and span.name == "SELECT"
            and span.parent_id is not None
        ):
            # this is a db query span
            sql = span.sql

            if self._source_span is None:
                # searching for the N+1 - maybe this span is the source that triggered it
                self._reset(span)
                return

            if span.parent_id != self._source_span.parent_id:
                # we have a new parent now, reset the detection
                self._reset(span)
                return

            if sql == self._source_sql:
                self._reset(span)
                return

            if self._n_sql is None or sql == self._n_sql:
                # we have a potential source and this is now a different query
                # with the same parent - maybe there's N of them
                self._n_sql = sql
                self._n_spans.append(span)
                return

            self._reset(span)

    def finish(self):
        if len(self._n_spans) > 1:
            self._save_result()

    def _fingerprint(self):
        return fingerprint(self._source_sql, self._n_sql)

    def _reset(self, span: Span):
        if len(self._n_spans) > 1:
            self._save_result()
        self._source_span = span
        self._source_sql = span.sql
        self._n_spans = []
        self._n_sql = None

    def _save_result(self):
        fingerprint = self._fingerprint()
        if fingerprint not in self.results:
            self.results[fingerprint] = AnalysisResult(
                analysis_type=AnalysisType.N_PLUS_ONE,
                queries=[self._source_sql, self._n_sql],
                tests=set(),
            )
        test = self.test_info(self._source_span)
        if test is not None:
            self.results[fingerprint].tests.add(test)


class SeqScanAnalyzer(Analyzer):
    # TODO: this is all very Postgres-specific
    # will need to abstract a lot of this when there are other plan formats

    def visit(self, span: Span):
        if self.metadata is None:
            return

        explain_data = self.metadata.get("explained")
        if explain_data is None:
            return

        if span.span_type == SpanType.DB and span.sql in explain_data:
            plan = explain_data[span.sql]["Plan"]
            if self._contains_seq_scan(plan):
                assert span.sql is not None
                f = fingerprint(span.sql)
                if f not in self.results:
                    self.results[f] = AnalysisResult(
                        analysis_type=AnalysisType.SEQ_SCAN,
                        queries=[span.sql],
                        tests=set(),
                    )
                test = self.test_info(span)
                if test is not None:
                    self.results[f].tests.add(test)

    def _contains_seq_scan(self, plan: dict) -> bool:
        if plan["Node Type"] == "Seq Scan":
            return True

        if "Plans" in plan:
            # has sub plans
            return any(
                [self._contains_seq_scan(sub_plan) for sub_plan in plan["Plans"]]
            )

        return False


class MissingIndexAnalyzer(Analyzer):
    def visit(self, span: Span):
        if self.metadata is None:
            return

        indexes = self.metadata.get("indexes")
        if indexes is None:
            return

        if span.span_type == SpanType.DB and span.name == "SELECT":
            assert span.sql is not None

            test = self.test_info(span)
            if not test:
                return

            f = fingerprint(span.sql)
            sql = span.sql

            # replace '%s' placeholders with '$N' where N=1..
            r = re.compile(r"\%s")
            n = len(r.findall(sql))
            for i in range(1, n + 1):
                sql = sql.replace("%s", f"${i}", 1)

            ast = parse_one(sql)

            # collect all table aliases
            table_aliases = {}
            for node in ast.find_all(exp.From):
                table_aliases[node.alias_or_name] = node.name
            for join in ast.find_all(exp.Join):
                tables = join.find_all(exp.Table)
                for table in tables:
                    table_aliases[table.alias_or_name] = table.name

            for where in ast.find_all(exp.Where):
                columns = where.find_all(exp.Column)

                # group columns by table - if there are multiple tables
                # then the database will scan each index and create bitmaps
                # that are combined together
                by_table = defaultdict(list)
                for column in columns:
                    table_name = table_aliases.get(column.table) or column.table
                    if not table_name:
                        continue
                    by_table[table_name].append(column.name)

                # for each table try and find an index that includes all columns
                # as a contiguous leading subset
                for table_name, column_names in by_table.items():
                    found_index = False
                    for index in indexes:
                        index = Index(**index)
                        index_table_name = (
                            table_aliases.get(index.table_name) or index.table_name
                        )
                        if table_name == index_table_name and index.indexes_columns(
                            column_names
                        ):
                            found_index = True
                            break
                    if not found_index:
                        if f not in self.results:
                            self.results[f] = AnalysisResult(
                                analysis_type=AnalysisType.MISSING_INDEX,
                                queries=[span.sql],
                                tests=set(),
                                extra=dict(),
                            )
                        extra = self.results[f].extra
                        if extra is not None:
                            extra[table_name] = column_names

            if f in self.results:
                self.results[f].tests.add(test)


analyzers: List[Type[Analyzer]] = [
    NPlusOneAnalyzer,
    MissingIndexAnalyzer,
    SeqScanAnalyzer,
]


def analyze(spans: Spans, metadata: Optional[dict] = None) -> Iterator[AnalysisResult]:
    for analyzer in analyzers:
        yield from analyzer(spans, metadata=metadata).analyze()
