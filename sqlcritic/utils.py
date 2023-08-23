import hashlib
import json
from typing import List


def fingerprint(*items: str) -> str:
    hashes = [hashlib.sha1(item.encode()).hexdigest() for item in items]
    combined = "-".join(hashes)
    return hashlib.sha1(combined.encode()).hexdigest()


def load_data(path: str) -> List[dict]:
    with open(path) as f:
        return json.load(f)
