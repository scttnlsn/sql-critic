import hashlib
import json
import os
import subprocess
from typing import List


def fingerprint(*items: List[str]) -> str:
    hashes = [hashlib.sha1(item.encode("utf-8")).hexdigest() for item in items]
    combined = "-".join(hashes)
    return hashlib.sha1(combined.encode("utf-8")).hexdigest()


def load_data(path: str) -> List[dict]:
    with open(path) as f:
        return json.load(f)


def current_git_sha() -> str:
    os.system("git config --global --add safe.directory /github/workspace")
    output = subprocess.check_output("git show --no-patch --format=%P", shell=True)
    return output.decode("utf-8").strip()
