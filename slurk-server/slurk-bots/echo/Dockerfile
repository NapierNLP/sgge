FROM python:3.9

RUN mkdir -p /usr/src/echo
WORKDIR /usr/src/echo

COPY echo/requirements.txt /usr/src/echo
RUN pip install --no-cache-dir -r requirements.txt

COPY echo /usr/src/echo

ENTRYPOINT ["python", "echo.py"]
