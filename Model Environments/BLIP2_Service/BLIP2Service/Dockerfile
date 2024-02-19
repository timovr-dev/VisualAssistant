# Use the nvidia/cuda:11.7.1-devel-ubuntu20.04 base image
FROM nvidia/cuda:11.7.1-devel-ubuntu20.04

# basic installations
RUN apt-get update -y
RUN apt-get install python3 python3-pip -y

# fast api & dependencies installation
RUN pip install --upgrade pip
RUN pip install fastapi uvicorn pydantic python-multipart

# BLIP2 installation
WORKDIR /BLIP2Service
COPY . /BLIP2Service
RUN pip install --no-cache-dir salesforce-lavis

# run LLaVA model API
#WORKDIR /LLaVA
#CMD ["python3", "model.py"]
