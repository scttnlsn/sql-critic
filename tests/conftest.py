from pathlib import Path

import pytest
import vcr

from sqlcritic.trace import parse_spans
from sqlcritic.utils import load_data


@pytest.fixture
def vcr_cassette(request):
    test_path = Path(request.node.fspath)
    test_filename = test_path.name.replace(".py", "")
    cassette_dir = test_path.parent / "cassettes" / test_filename
    with vcr.use_cassette(
        str(cassette_dir / f"{request.node.name}.yaml"),
        record_mode="once",
        filter_headers=["authorization"],
        match_on=["method", "scheme", "host", "port", "path"],
    ) as cassette:
        yield cassette


@pytest.fixture
def spans():
    data = load_data("tests/fixtures/test-spans.json")
    return parse_spans(data)
