import json
from typing import Optional

import boto3
from botocore.exceptions import ClientError


class Storage:
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, bucket: str):
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        self.bucket = bucket
        self.s3 = self.session.resource("s3")

    def put(self, sha: str, data: dict):
        obj = self.s3.Object(self.bucket, f"{sha}.json")
        obj.put(Body=json.dumps(data))

    def get(self, sha: str) -> Optional[dict]:
        try:
            obj = self.s3.Object(self.bucket, f"{sha}.json")
            res = obj.get()
            return json.loads(res["Body"].read())
        except ClientError as err:
            err_code = err.response["Error"]["Code"]
            if err_code == "NoSuchKey" or err_code == "AccessDenied":
                return None
            else:
                raise err
