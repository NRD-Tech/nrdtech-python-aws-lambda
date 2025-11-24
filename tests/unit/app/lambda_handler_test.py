import json
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv
from mangum import Mangum

load_dotenv()


def _is_mangum_handler():
    """Check if the handler is a Mangum instance (API Gateway)."""
    from app.lambda_handler import lambda_handler

    return isinstance(lambda_handler, Mangum)


def test_eventbridge_handler():
    """Test EventBridge scheduled lambda handler."""
    from app.lambda_handler import lambda_handler

    # Skip if Mangum handler is active (Mangum doesn't support EventBridge)
    if _is_mangum_handler():
        pytest.skip(
            "EventBridge handler not active - Mangum handler is active. Uncomment EventBridge section in lambda_handler.py to test"
        )

    # EventBridge event structure
    mock_event = {
        "version": "0",
        "id": "test-event-id",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": "2024-01-01T00:00:00Z",
        "region": "us-west-2",
        "detail": {},
    }
    mock_context = MagicMock()

    response = lambda_handler(mock_event, mock_context)

    assert response["statusCode"] == 200
    assert response["body"] == "Done"


def test_sqs_handler():
    """Test SQS triggered lambda handler."""
    from app.lambda_handler import lambda_handler

    # Skip if Mangum handler is active (Mangum doesn't support SQS)
    if _is_mangum_handler():
        pytest.skip(
            "SQS handler not active - Mangum handler is active. Uncomment SQS section in lambda_handler.py to test"
        )

    # SQS event structure
    mock_event = {
        "Records": [
            {
                "messageId": "test-message-id",
                "receiptHandle": "test-receipt-handle",
                "body": json.dumps({"key": "value"}),
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": "1234567890000",
                },
                "messageAttributes": {},
                "md5OfBody": "test-md5",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-west-2:123456789012:test-queue",
                "awsRegion": "us-west-2",
            }
        ]
    }
    mock_context = MagicMock()

    response = lambda_handler(mock_event, mock_context)

    assert response["statusCode"] == 200
    assert response["body"] == "Done"


def test_api_gateway_handler():
    """Test API Gateway lambda handler."""
    from app.lambda_handler import lambda_handler

    # Skip if not Mangum handler
    if not _is_mangum_handler():
        pytest.skip(
            "API Gateway handler not active - Mangum handler is not active. Uncomment API Gateway section in lambda_handler.py to test"
        )

    # API Gateway v1 event structure (required by Mangum)
    mock_event = {
        "httpMethod": "GET",
        "path": "/healthcheck",
        "headers": {
            "Content-Type": "application/json",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-request-id",
            "stage": "test",
            "httpMethod": "GET",
            "path": "/healthcheck",
            "accountId": "123456789012",
            "apiId": "test-api-id",
            "protocol": "HTTP/1.1",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {
                "sourceIp": "127.0.0.1",
            },
        },
        "resource": "/healthcheck",
    }
    mock_context = MagicMock()

    response = lambda_handler(mock_event, mock_context)

    # API Gateway responses have statusCode and body (may be JSON string)
    assert "statusCode" in response
    assert response["statusCode"] == 200
    assert "body" in response
