#
FROM python:3.9

#
WORKDIR /code/

#
COPY ./requirements.txt /code/requirements.txt

#
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#
COPY ./src /code/app

#
WORKDIR /code/app

#
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg
