from app.lambda_handler import lambda_handler
from dotenv import load_dotenv

load_dotenv()


def test_lambda_handler():
    # Mock input event and context
    mock_event = {}
    mock_context = {}

    # Call the handler
    response = lambda_handler(mock_event, mock_context)

    # Assertions
    assert response["statusCode"] == 200
    assert response["body"] == "Done"
