FROM python:3.8-slim-buster

WORKDIR /app

RUN pip install pika sympy python-decouple

COPY prover.py .
COPY .env .

CMD ["python", "prover.py"]
