from pathlib import Path

import pytest
import vcr


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
