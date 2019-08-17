FROM python:latest

RUN git clone https://github.com/xtracthub/xtract-images
RUN cd xtract-images && pip install -r requirements.txt

WORKDIR /xtract-images

ENTRYPOINT ["python", "xtract_images_main.py"]