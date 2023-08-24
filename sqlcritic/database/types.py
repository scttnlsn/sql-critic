from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Index:
    schema_name: str
    table_name: str
    index_name: str
    columns: Tuple[str, ...]
