FROM public.ecr.aws/lambda/python:3.12

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy pyproject.toml and poetry.lock for dependency installation
COPY pyproject.toml poetry.lock ./

# NOTE: Use this if you need to access private codeartifact shared python libraries
# ARG CODEARTIFACT_TOKEN
# ENV CODEARTIFACT_TOKEN=${CODEARTIFACT_TOKEN}
# RUN ~/.local/bin/poetry config http-basic.mycompany aws ${CODEARTIFACT_TOKEN}

# Install dependencies using Poetry (only production dependencies)
RUN ~/.local/bin/poetry install --only main --no-dev

# Locate Poetry's virtual environment and copy dependencies to the Lambda path
RUN VENV_PATH=$(~/.local/bin/poetry env info --path) && \
    cp -r ${VENV_PATH}/lib/python3.12/site-packages/* ${LAMBDA_TASK_ROOT}/

# Copy function code
COPY src/ ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD ["app.lambda_handler.lambda_handler"]
