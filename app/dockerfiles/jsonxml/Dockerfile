FROM python:latest

MAINTAINER Ryan Wong

RUN git clone https://github.com/xtracthub/xtract-jsonxml
WORKDIR xtract-jsonxml

COPY requirements.txt /
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "xtract_jsonxml_main.py"]
