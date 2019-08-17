FROM python:latest

RUN git clone https://github.com/xtracthub/xtract-keyword

WORKDIR xtract-keyword


COPY requirements.txt /
RUN pip install -U nltk
RUN pip install -r requirements.txt


ENTRYPOINT ["python", "xtract_keyword_main.py"]
