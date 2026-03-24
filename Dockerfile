FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
COPY wheels/ ./wheels/
RUN pip install --no-index --find-links=./wheels -r requirements.txt
COPY . .
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
