FROM python:3.7

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update -y
RUN apt install libgl1-mesa-glx -y

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN pip3 install pyinstaller==3.6
