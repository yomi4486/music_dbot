# ベースイメージの読み込み
FROM alpine:3.14
WORKDIR /usr/app
COPY ./ /usr/app
RUN apk update
RUN apk add --no-cache python3-dev && \
    apk add --no-cache py3-pip && \
    apk add --no-cache ffmpeg
RUN pip install --ignore-installed distlib && \
    pip install pipenv && \
    pip install --upgrade pipenv
RUN pipenv --python 3.9.17
RUN pipenv install -r /usr/app/requirements.txt
CMD pipenv run python -m dbot