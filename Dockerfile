FROM python:3.7

LABEL MAINTAINER rafael.mueller1@gmail.com

ADD ./requirements.txt .
RUN pip install -r requirements.txt

ADD ./logging.conf .

# Copy credentials into container
ADD .credentials.yaml .

# Copy source code into container
ADD ./metadata_registration_api /metadata_registration_api
WORKDIR /

EXPOSE 8000

CMD ["gunicorn", \
        "--workers", "4", \
        "--bind", "0.0.0.0", \
        "--log-config", "/logging.conf", \
        "metadata_registration_api.app:create_app(config='CONTAINER')"]

