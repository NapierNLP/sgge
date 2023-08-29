FROM python:3.9

RUN mkdir -p /usr/src/qasum
WORKDIR /usr/src/qasum

COPY qasum/requirements.txt /usr/src/qasum
RUN pip install --no-cache-dir -r requirements.txt

COPY qasum /usr/src/qasum

ENTRYPOINT ["python", "main.py"]
