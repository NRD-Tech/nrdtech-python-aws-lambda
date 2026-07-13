.PHONY: format lint test run

format:
	poetry run ruff format app tests setup_lib setup.py
	poetry run ruff check --fix app tests setup_lib setup.py

lint:
	poetry run ruff check app tests setup_lib setup.py
	poetry run mypy app

test:
	poetry run pytest tests/unit --cov=app --cov-fail-under=60

run:
	PYTHONPATH=app poetry run python -c "from app import logging_setup; logging_setup.configure_logging(); print('ok')"
