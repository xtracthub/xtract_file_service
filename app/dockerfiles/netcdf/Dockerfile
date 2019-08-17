FROM python:latest

MAINTAINER Ryan Wong

RUN git clone https://github.com/xtracthub/xtract-netcdf

WORKDIR xtract-netcdf
COPY requirements.txt /

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "xtract_netcdf_main.py"]

