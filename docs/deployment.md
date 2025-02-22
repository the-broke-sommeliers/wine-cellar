# Deployment
The easiest way to run Wine Cellar is by using docker as described below.

## Docker Deployment

### Development / Demo Mode

!!! Note

    Not for production use.

#### Steps:

1. Copy the development environment configuration:
   ```sh
   cp .env.dev-sample .env.dev
   ```
2. Build the Docker image:
   ```sh
   docker build -t wine-cellar-dev .
   ```
3. Start the application:
   ```sh
   docker compose up
   ```

---

### Production Setup

!!! Note

    This setup is under development. Proceed with caution.

!!! Note

    When using podman instead of docker you might have to add `:z` to the
    volumes to allow sharing them between containers and make SELinux happy.

#### Option 1: Using a Reverse Proxy

**Prerequisites:**

- A configured reverse proxy.
- Properly set `.env` files.

#### Steps:

1. Copy and configure environment files:
   ```sh
   cp .env.prod.db-sample .env.prod.db
   cp .env.prod-sample .env.prod
   ```
2. Edit `.env` files with secure credentials.
3. Start the production container:
   ```sh
   docker compose -f docker-compose.prod.yml up
   ```
4. Configure your reverse proxy to forward traffic to `http://127.0.0.1:8085`.

---

#### Option 2: Standalone Deployment with Letsencrypt

**Prerequisites:**

- No conflicting web server on ports 80 and 443.
- Domain name configured in `caddy/Caddyfile`.
- Secure `.env` files.

#### Steps:

1. Copy and configure environment files:
   ```sh
   cp .env.prod.db-sample .env.prod.db
   cp .env.prod-sample .env.prod
   ```
2. Edit `.env` files with secure credentials.
3. Update `caddy/Caddyfile` by replacing `:80` with your
   domain.
4. Start the production container:
   ```sh
   docker compose -f docker-compose.prod.full.yml up
   ```
