FROM python:3.10.8-alpine3.16 AS build
COPY . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
ENV PYTHONPATH /app
CMD ["python", "-m", "sqlcritic.action"]