# PROVIDED: the production image from the earlier lab (multi-stage, slim, non-root). Both the API and the worker use it.
FROM python:3.12-slim AS build
WORKDIR /build
COPY pollie/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=build /install /usr/local
COPY pollie/pollie ./pollie
USER 10001
EXPOSE 8000
HEALTHCHECK NONE
CMD ["uvicorn", "pollie.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
