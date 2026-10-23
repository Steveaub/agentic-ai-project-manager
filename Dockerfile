FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home planner
COPY pm ./pm
COPY web ./web
RUN mkdir data && chown planner:planner data
USER planner
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "pm.api:app", "--host", "0.0.0.0", "--port", "8000"]
