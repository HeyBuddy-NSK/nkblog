FROM python:3.11-alpine

ENV FLASK_APP nkblog.py
ENV FLASK_CONFIG docker

RUN adduser -D nkblog
USER nkblog

WORKDIR /home/nkblog

COPY requirements requirements
RUN python -m venv venv
RUN venv/bin/pip install -r requirements/docker.txt

COPY app app
COPY migrations migrations
COPY nkblog.py config.py boot.sh ./

# runtime configuration
EXPOSE 5000
ENTRYPOINT ["./boot.sh"]