import json
import logging

from infrastructure.observability.logging import JsonFormatter
from infrastructure.observability.request_context import set_request_id


def test_formats_a_record_as_json_including_the_request_id():
    set_request_id("req-1")
    record = logging.LogRecord(
        name="app", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    formatter = JsonFormatter()

    output = json.loads(formatter.format(record))

    assert output == {"level": "INFO", "message": "hello world", "logger": "app", "request_id": "req-1"}
