from sqlcritic.storage import Storage


def test_put_get(vcr_cassette):
    storage = Storage(
        access_key_id="test",
        secret_access_key="test",
        bucket="sql-critic-demo",
    )

    storage.put("testing", {"foo": "bar"})

    result = storage.get("testing")
    assert result == {"foo": "bar"}


def test_get_missing(vcr_cassette):
    storage = Storage(
        access_key_id="test",
        secret_access_key="test",
        bucket="sql-critic-demo",
    )

    result = storage.get("missing-key")
    assert result is None
