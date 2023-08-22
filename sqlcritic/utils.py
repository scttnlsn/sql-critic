import hashlib
import json
from typing import List


def fingerprint(*items: List[str]) -> str:
    hashes = [hashlib.sha1(item.encode("utf-8")).hexdigest() for item in items]
    combined = "-".join(hashes)
    return hashlib.sha1(combined.encode("utf-8")).hexdigest()


def load_data(path: str) -> List[dict]:
    with open(path) as f:
        return json.load(f)
