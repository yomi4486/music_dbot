# ベースイメージの読み込み
FROM alpine:3.14
WORKDIR /usr/app
COPY ./ /usr/app
RUN apk update
RUN apk add --no-cache python3-dev && \
    apk add --no-cache py3-pip && \
    apk add --no-cache ffmpeg && \
    pip3 install --upgrade pip
RUN pip install -r requirements.txt
CMD python3 -m dbot