# pull official base image
FROM python:3.13.3-slim-bookworm

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install git netcat-traditional curl libpq-dev libpq5 -y
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs \
    build-essential && node --version && npm --version

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
