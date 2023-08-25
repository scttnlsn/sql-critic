from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class Index:
    schema_name: str
    table_name: str
    index_name: str
    columns: Tuple[str, ...]

    def indexes_columns(self, column_names: List[str]) -> bool:
        n = len(column_names)
        return self.columns[:n] == tuple(column_names)
