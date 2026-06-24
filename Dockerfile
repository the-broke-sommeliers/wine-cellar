# pull official base image
FROM python:3.13.3-slim-bookworm

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/src/app/.venv/bin:$PATH"

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.11.14@sha256:1025398289b62de8269e70c45b91ffa37c373f38118d7da036fb8bb8efc85d97 /uv /uvx /bin/

# install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install git netcat-traditional curl libpq-dev libpq5 build-essential -y
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y nodejs

# copy project
COPY . .

# install python dependencies
RUN uv sync --frozen --no-dev --group prod

# install js dependencies and build
RUN npm install
RUN npm run build

# copy entrypoint.sh
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /usr/src/app/entrypoint.sh
RUN chmod +x /usr/src/app/entrypoint.sh

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
