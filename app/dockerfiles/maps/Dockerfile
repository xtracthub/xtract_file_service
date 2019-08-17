FROM python:latest

MAINTAINER Ryan Wong

RUN git clone https://github.com/xtracthub/xtract-maps

WORKDIR xtract-maps
COPY requirements.txt /

# Install dependencies
RUN pip install -r requirements.txt
RUN apt-get update
RUN apt-get install tesseract-ocr -y libtesseract-dev -y

ENTRYPOINT ["python", "xtract_maps_main.py"]
