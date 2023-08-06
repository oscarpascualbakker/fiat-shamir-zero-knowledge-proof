FROM python:3.8-slim-buster

WORKDIR /app

RUN pip install pika sympy

COPY prover.py .

CMD ["python", "prover.py"]
