FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py api.py dataset.csv ./
COPY src ./src
COPY .streamlit ./.streamlit
COPY models/predictor.joblib ./models/predictor.joblib
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
