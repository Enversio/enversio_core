# Railway deployment — enversio_core (Saleor)

The upstream `/Dockerfile` is used as-is apart from one required change: the
Railway Metal builder rejects a `--mount=type=cache` without an `id=`, so the
uv cache mount is now `--mount=type=cache,id=uv-cache,…`. Without it the build
fails immediately with

    dockerfile invalid: flag '--mount=type=cache,target=/root/.cache/uv' is missing an id argument at Line 15

## Services

The services are declared in Railway Infrastructure as Code, which lives in the
connector repository at `enversio-flow-connector/.railway/railway.ts` — Railway
IaC is one file per project, and all three Enversio repositories share a single
Railway project. Railway's older Config as Code (`railway.json`) is deprecated
and new services cannot opt into it, so there is deliberately no such file here.

| Railway service | Start command | Role | Public |
|---|---|---|---|
| `saleor-web` | `uvicorn saleor.asgi:application …` | ASGI app (`/graphql/`) | ✅ |
| `saleor-worker` | `celery … worker` | webhooks, exports, search reindex | |
| `saleor-beat` | `celery … beat` | scheduled tasks from `CELERY_BEAT_SCHEDULE` | |

Migrations run as `saleor-web`'s **pre-deploy command**, so they complete once
before the new container takes traffic rather than racing at boot in every
replica.

## Required variables

| Variable | Notes |
|---|---|
| `SECRET_KEY` | Django secret. Not optional — settings only auto-generate one when `DEBUG` is on. |
| `DATABASE_URL` | `postgres://…`. Read through `dj_database_url`. |
| `CELERY_BROKER_URL` | Redis or RabbitMQ. |
| `CACHE_URL` | Redis. |
| `ALLOWED_HOSTS` | The Railway domain. Requests with any other `Host` are rejected. |
| `ALLOWED_CLIENT_HOSTS` | Storefront/dashboard origins. |
| `ALLOWED_GRAPHQL_ORIGINS` | CORS origins for `/graphql/`. |
| `DEFAULT_FROM_EMAIL`, `EMAIL_URL` | Outbound mail. |
| `RSA_PRIVATE_KEY` | JWT signing key. Generated per-instance if unset — which invalidates every issued token on redeploy, so set it explicitly. |
| `ENABLE_SSL` | `True` behind the Railway edge. |

## Media files

The image creates `/app/media`, but a container filesystem does not survive a
redeploy. Uploaded product images must go to object storage — set the
`AWS_*` block (`AWS_MEDIA_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_REGION_NAME`) against S3
or Cloudflare R2. A Railway volume mounted at `/app/media` also works, but only
while `saleor-web` stays at one replica.

Static files are already collected into the image at build time, so they need
no runtime storage.

## Resources

Saleor is not a small service: expect the web container to need ~1 GB and the
Celery worker ~1 GB before it is comfortable. The default `--workers=2` in the
image CMD is carried over into `web.json`.
