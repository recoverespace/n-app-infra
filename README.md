

# HOW TO START?
1. Create `.env` file
2. Put environment variables inside
```bash
REDIS_DSN=redis://127.0.0.1:6379/1
POSTGRES_DSN=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/backend
FIREBASE_CERTIFICATE='{
  "type": "service_account",
  "project_id": "<your-project-id>",
  "private_key_id": "<redacted>",
  "private_key": "<redacted>",
  "client_email": "<service-account>@<your-project-id>.iam.gserviceaccount.com",
  "client_id": "<redacted>",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/<redacted>",
  "universe_domain": "googleapis.com"
}'
```
# Install PDM

```bash
brew install pdm
```

# Install packages

```bash
pdm install -d -G:all
```

# Create network

`docker network create -d bridge recovered-network`

# Run Postgres/Redis/Grafana

```bash
docker compose \
  --env-file .env.dev \
  -f docker-compose.yml \
  -f docker-compose.api.yml \
  up -d --build
```

# Open Docs
http://0.0.0.0:8000/docs


# Deployment

## Build images and push

```bash
gcloud auth print-access-token | podman login -u oauth2accesstoken --password-stdin us-central1-docker.pkg.dev
podman build . --target api -t us-central1-docker.pkg.dev/rcvrd-1777d/recovered-images/recovered-backend-api:develop --platform linux/amd64 && podman push us-central1-docker.pkg.dev/rcvrd-1777d/recovered-images/recovered-backend-api:develop
podman build . --target admin -t us-central1-docker.pkg.dev/rcvrd-1777d/recovered-images/recovered-backend-admin:develop --platform linux/amd64 && podman push us-central1-docker.pkg.dev/rcvrd-1777d/recovered-images/recovered-backend-admin:develop
```

## Upgrade Helm chart

```bash
helm upgrade --install api ./k8s/chart/ -f k8s/chart/values.yaml -f k8s/envs/prod.yaml --namespace=apps --atomic --cleanup-on-fail --debug
```
