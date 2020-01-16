## Testing aws auth type manual/QA script

```python
from datadog_checks.http_check import HTTPCheck
from mock import patch

def test_check_with_aws_auth_type(aggregator):
    # Set credentials using one of the boto credentials configuration
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#configuring-credentials
    # e.g. env var:
    # os.environ['AWS_ACCESS_KEY_ID'] = 'AAAA'
    # os.environ['AWS_SECRET_ACCESS_KEY'] = 'BBBB'

    instance = {
        'name': 'aws_s3_content_match',
        'url': 'https://s3.amazonaws.com/my-bucket-abcd',   # link to your bucket link
        'timeout': 1,
        'auth_type': 'aws',
        'aws_host': 's3.amazonaws.com',
        'aws_region': 'us-east-1',
        'aws_service': 's3',
        'content_match': 'my-folder-007',                   # something present in your s3 bucket
    }
    with patch('datadog_checks.http_check.http_check.get_ca_certs_path'):
        http_check = HTTPCheck('http_check', {}, [instance])
    http_check.check(instance)

    aws_tags = ['url:https://s3.amazonaws.com/test-bucket-alex-2020-01-16', 'instance:aws_s3_content_match']

    # content expected to match, hence status=HTTPCheck.OK
    aggregator.assert_service_check(
        HTTPCheck.SC_STATUS, status=HTTPCheck.OK, tags=aws_tags, count=1
    )
```
