# pull official base image
FROM python:3.14.2-slim-bookworm

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install git netcat-traditional curl libpq-dev libpq5 build-essential -y
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y nodejs 

# copy project
COPY . .

# install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements/prod.txt
RUN npm install
RUN npm run build

# copy entrypoint.sh
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /usr/src/app/entrypoint.sh
RUN chmod +x /usr/src/app/entrypoint.sh

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
