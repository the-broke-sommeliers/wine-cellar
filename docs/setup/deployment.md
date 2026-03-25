# Deployment
The easiest way to run Wine Cellar is by using docker as described below.

## Production Setup

???+ Tip

    When using podman instead of docker you might have to add `:z` or `:Z` to the
    volumes to allow sharing them between containers and make SELinux happy.

### Option 1: Docker + Reverse Proxy

#### Prerequisites

- A configured reverse proxy (e.g. nginx or caddy).

#### Steps

##### 1. Clone the repository
   ```sh
   git clone https://github.com/the-broke-sommeliers/wine-cellar.git
   ```
##### 2. Checkout the latest release
   ```sh
   git checkout 0.5.0
   ```
##### 3. Copy and configure environment files:
   ```sh
   cp .env.prod.db-sample .env.prod.db
   cp .env.prod-sample .env.prod
   ```
##### 4. Edit both `.env` files with secure credentials and your desired settings.
##### 5. Start the production container:
=== "Docker"
    ```sh
    docker compose -f docker-compose.prod.yml up -d
    ```
=== "Podman"
    ```sh
    podman-compose -f docker-compose.prod.yml up -d
    ```
##### 6. Configure your reverse proxy to forward traffic to `http://127.0.0.1:8085`.


#### Update

To update to a newer version do the following steps:

##### 1. Stop the containers
=== "Docker"
    ```sh
    docker compose -f docker-compose.prod.yml down
    ```
=== "Podman"
    ```sh
    podman-compose -f docker-compose.prod.yml down
    ```
##### 2. Fetch latest release
   ```sh
   git fetch
   ```
##### 3. Checkout the latest release
   ```sh
   git checkout <latest version>
   ```
##### 4. Check if env files had changes  
   Compare your `.env.prod` and `env.prod.db` against the sample files to check if there's been any changes. If so, copy them over.
##### 5. Pull new image
=== "Docker"
    ```sh
    docker compose -f docker-compose.prod.yml pull
    ```
=== "Podman"
    ```sh
    podman-compose -f docker-compose.prod.yml pull
    ```
##### 6. Start the containers:
=== "Docker"
    ```sh
    docker compose -f docker-compose.prod.yml up -d
    ```
=== "Podman"
    ```sh
    podman-compose -f docker-compose.prod.yml up -d
    ```

#### Email Setup

Wine Cellar can notify you, including sending 'drink by' reminders for your wines.
To enable email notifications, configure the email backend and credentials in your `.env-prod` file:

```
DJANGO_EMAIL_HOST=smtp.example.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_HOST_USER=your@email.com
DJANGO_EMAIL_HOST_PASSWORD=yourpassword
DJANGO_EMAIL_USE_TLS=
DJANGO_EMAIL_USE_SSL=
DJANGO_DEFAULT_FROM_EMAIL=Wine Cellar <your@email.com>
```

???+ Info
    USE_TLS and USE_SSL are mutual exclusive, only one may be set to True.

#### AI Setup

Wine Cellar supports AI-powered wine label scanning to automatically extract wine details from photos to make adding new wines
a bit easier.

To enable this feature, configure the following in your `.env-prod` file:
```
AI_MODEL=gemini/gemini-2.5-flash
AI_API_KEY=your-api-key
```

???+ Tip
    [Google Gemini](https://aistudio.google.com) offers a free tier with no credit card required.
    The free quota (~50 requests/day) is sufficient for personal use.
    Simply create an API key at [Google AI Studio](https://aistudio.google.com) and use `gemini/gemini-2.5-flash` as the model.

???+ Info
    Other providers such as OpenAI (`gpt-4o`) and Anthropic (`anthropic/claude-3-5-sonnet-20241022`) are also supported.
    See [LiteLLM's documentation](https://docs.litellm.ai/docs/providers) for a full list of supported models and providers.

#### Sample NGINX config

Below is a sample nginx config using Letsencrypt for your reverse proxy. 

???+ Info
    Replace `<your full domain>` with the domain you want to use and make sure you have a Letsencrypt certificate for it already. Alternatively remove/modify the ssl block as needed.

```
server {
  listen 443 ssl http2;
  listen [::]:443 ssl http2;

  server_name <your full domain>;

  access_log  /var/log/nginx/<your full domain>.access.log;                      
  error_log  /var/log/nginx/<your full domain>.error.log error;                  

  location / {
    proxy_set_header Connection $http_connection;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_pass http://127.0.0.1:8085;

    client_max_body_size 500M;
    client_body_buffer_size 50M;
  }

  ssl_certificate /etc/letsencrypt/live/<your full domain>/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/<your full domain>/privkey.pem;
  ssl_session_timeout 1d;
  ssl_session_cache shared:MozSSL:10m;  # about 40000 sessions
  ssl_session_tickets off;

  # modern configuration
  ssl_protocols TLSv1.3;
  ssl_prefer_server_ciphers off;

  # HSTS (ngx_http_headers_module is required) (63072000 seconds)
  add_header Strict-Transport-Security "max-age=63072000" always;

  # replace with the IP address of your resolver
  resolver 9.9.9.9 [2620:fe::fe] valid=300s;
}
```
### SSO
see [SSO](sso.md)