FROM bitcoin-mlops:latest

RUN pip install --no-cache-dir prometheus-client

COPY app.py .

EXPOSE 8080

CMD ["python", "app.py"]