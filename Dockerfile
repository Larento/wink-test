FROM python:3.13

RUN pip install pdm

WORKDIR /app
COPY pyproject.toml .
COPY pdm.lock .
RUN pdm install --production

COPY src src
ENTRYPOINT pdm run fastapi run src/wink_test/main.py --port 80