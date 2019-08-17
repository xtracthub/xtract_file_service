FROM python:latest

MAINTAINER Ryan Wong

RUN git clone https://github.com/xtracthub/xtract-tabular
WORKDIR xtract-tabular

COPY requirements.txt /
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "xtract_tabular_main.py"]
