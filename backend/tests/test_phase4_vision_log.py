"""Phase 4 step 0: a failing vision provider's own error message reaches the log (never the image or the key)."""
import httpx

import vision


def reply(status, payload):
    return httpx.Response(status, json=payload)


def test_error_reason_uses_the_providers_message():
    text = vision.error_reason(reply(503, {"error": {"code": 503, "message": "This model is currently experiencing high demand."}}))
    assert text == ": This model is currently experiencing high demand."


def test_error_reason_is_short_and_tolerant():
    assert len(vision.error_reason(reply(400, {"error": {"message": "x" * 1000}}))) <= 202
    assert vision.error_reason(reply(500, {"error": "plain string"})) == ": plain string"
    assert vision.error_reason(httpx.Response(502, text="<html>bad gateway</html>")) == ""
    assert vision.error_reason(reply(500, ["not", "a", "dict"])) == ""
    assert vision.error_reason(reply(500, {})) == ""
