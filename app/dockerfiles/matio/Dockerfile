FROM python:latest

MAINTAINER Ryan Wong 

RUN git clone https://github.com/materials-data-facility/MaterialsIO.git && cd MaterialsIO && pip install -e . \
    && pip install -r requirements.txt

COPY xtract_matio_main.py /


ENTRYPOINT ["python", "xtract_matio_main.py"]
