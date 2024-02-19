# Use the nvidia/cuda:11.7.1-devel-ubuntu20.04 base image
FROM nvidia/cuda:11.7.1-devel-ubuntu20.04

# basic installations
RUN apt-get update -y
RUN apt-get install python3 python3-pip -y

# fast api & dependencies installation
RUN pip install --upgrade pip
RUN pip install fastapi uvicorn pydantic

# LLaVA installation
WORKDIR /LLaVA
COPY . /LLaVA
WORKDIR /LLaVA/LLaVA_repository
RUN pip install --no-cache-dir -e ./

# run LLaVA model API
WORKDIR /LLaVA
CMD ["python3", "model.py"]
