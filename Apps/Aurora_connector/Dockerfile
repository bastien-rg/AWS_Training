FROM ubuntu:22.04

RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip install nicegui psycopg2-binary boto3

COPY aurora_connector.py /

EXPOSE 8765
CMD ["python3", "aurora_connector.py"]