# Deployment
The easiest way to run Wine Cellar is by using docker as described below.

## Production Setup

???+ Tip

    When using podman instead of docker you might have to add `:z` to the
    volumes to allow sharing them between containers and make SELinux happy.

### Option 1: Docker + Reverse Proxy

#### Prerequisites

- A configured reverse proxy (e.g. nginx or caddy).

#### Steps

1. Clone the repository
   ```sh
   git clone https://github.com/the-broke-sommeliers/wine-cellar.git
   ```
2. Checkout the latest release
   ```sh
   git checkout 0.4.0
   ```
3. Copy and configure environment files:
   ```sh
   cp .env.prod.db-sample .env.prod.db
   cp .env.prod-sample .env.prod
   ```
4. Edit both `.env` files with secure credentials and your desired settings.
5. Start the production container:
   ```sh
   docker compose -f docker-compose.prod.yml up
   ```
6. Configure your reverse proxy to forward traffic to `http://127.0.0.1:8085`.


#### Update

To update to a newer version do the following steps:

1. Stop the containers
   ```sh
   docker compose -f docker-compose.prod.yml down
   ```
2. Fetch latest release
   ```sh
   git fetch
   ```
3. Checkout the latest release
   ```sh
   git checkout <latest version>
   ```
4. Check if env files had changes  
   Compare your `.env.prod` and `env.prod.db` against the sample files to check if there's been any changes. If so, copy them over.
5. Pull new image
   ```sh
   docker compose -f docker-compose.prod.yml pull
   ```
6. Start the containers:
   ```sh
   docker compose -f docker-compose.prod.yml up
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

  ssl_certificate /etc/letsencrypt/live/<your full domain>/fullchain.pem; # managed by Certbot
  ssl_certificate_key /etc/letsencrypt/live/<your full domain>/privkey.pem; # managed by Certbot
  ssl_session_timeout 1d;
  ssl_session_cache shared:MozSSL:10m;  # about 40000 sessions
  ssl_session_tickets off;

  # modern configuration
  ssl_protocols TLSv1.3;
  ssl_prefer_server_ciphers off;

  # HSTS (ngx_http_headers_module is required) (63072000 seconds)
  add_header Strict-Transport-Security "max-age=63072000" always;

  # OCSP stapling
  ssl_stapling on;
  ssl_stapling_verify on;

  # verify chain of trust of OCSP response using Root CA and Intermediate certs
  ssl_trusted_certificate /etc/letsencrypt/live/wine.dehm.dev/chain.pem;

  # replace with the IP address of your resolver
  resolver 9.9.9.9 [2620:fe::fe] valid=300s;
}
```