FROM public.ecr.aws/lambda/python:3.14 AS builder

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true && \
    poetry install --only main --no-interaction --no-ansi --no-root

FROM public.ecr.aws/lambda/python:3.14

# Lambda images run as a dedicated non-root runtime user provided by the base image.
COPY --from=builder /var/task/.venv/lib/python3.14/site-packages/ ${LAMBDA_TASK_ROOT}/
COPY app/ ${LAMBDA_TASK_ROOT}/app/

ENV PYTHONPATH="${PYTHONPATH}:${LAMBDA_TASK_ROOT}:${LAMBDA_TASK_ROOT}/app" \
    PYTHONUNBUFFERED=1

CMD ["app.lambda_handler.lambda_handler"]
