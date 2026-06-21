# Deployment

This project is currently deployed as two separate services:

```txt
Frontend: Vercel
Backend: Render
```

The React frontend is built and hosted by Vercel. The FastAPI backend runs as a Render Web Service. The frontend talks to the backend through the backend `/api` routes.

## Architecture

```txt
Browser
  |
  v
Vercel React app
  |
  v
Render FastAPI backend
  |
  v
PostgreSQL / Supabase / OpenAI
```

The backend API routes are all prefixed with `/api`, for example:

```txt
/api/auth/login
/api/auth/me
/api/checklists
/api/files
/api/ai/checklists/...
```

This keeps frontend browser routes separate from backend JSON routes.

## Frontend deployment: Vercel

The frontend lives in:

```txt
frontend/checklist-copilot-frontend
```

Vercel project settings:

```txt
Framework Preset: Vite
Root Directory: frontend/checklist-copilot-frontend
Install Command: npm ci
Build Command: npm run build / vite build
Output Directory: dist
```

### Frontend environment variables

Set this in Vercel:

```txt
VITE_API_BASE_URL=https://<render-backend-domain>.onrender.com/api
```

Example:

```txt
VITE_API_BASE_URL=https://checkly-backend-0os9.onrender.com/api
```

Important: Vite environment variables are injected at build time. If this value is changed in Vercel, redeploy the frontend.

## Backend deployment: Render

The backend lives in:

```txt
backend
```

Render service settings:

```txt
Service Type: Web Service
Runtime: Python 3
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render provides the `$PORT` variable automatically.

The FastAPI app entrypoint is:

```txt
backend/app/main.py
```

So the app import path is:

```txt
app.main:app
```

## Backend environment variables

Set the backend variables in Render. Required variables include:

```txt
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>
JWT_SECRET_KEY=<long-random-secret>
OPENAI_API_KEY=<openai-api-key>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<supabase-service-role-key>
SUPABASE_IMAGES_BUCKET=images
SUPABASE_PDFS_BUCKET=pdfs
```

Optional variables:

```txt
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
OPENAI_MODEL=gpt-4o-mini
```

## CORS

CORS is configured by the backend in `backend/app/main.py` using values from `backend/app/core/config.py`.

For production, Render must allow the Vercel frontend origin:

```txt
BACKEND_CORS_ORIGINS=["https://<vercel-frontend-domain>.vercel.app"]
```

Example:

```txt
BACKEND_CORS_ORIGINS=["https://checkly-hub.vercel.app"]
```

Important details:

- The value must be valid JSON because the setting is typed as `list[str]`.
- Include `https://`.
- Do not include a trailing slash.
- The origin must exactly match the URL opened in the browser.

If multiple Vercel domains should work, include all of them:

```txt
BACKEND_CORS_ORIGINS=["https://checkly-hub.vercel.app","https://another-preview-domain.vercel.app"]
```

For production, `BACKEND_CORS_ORIGIN_REGEX` can be left unset unless a regex-based origin rule is intentionally needed.

## Common deployment issues

### Vercel fails at `npm ci`

If Vercel fails during install with a message like:

```txt
npm ci can only install packages when your package.json and package-lock.json are in sync
```

Fix locally:

```bash
cd frontend/checklist-copilot-frontend
npm install
npm ci
npm run build
```

Then commit and push the updated lockfile:

```bash
git add package-lock.json package.json
git commit -m "Fix frontend package lock"
git push
```

### Render crashes parsing `BACKEND_CORS_ORIGINS`

If Render logs show:

```txt
SettingsError: error parsing value for field "BACKEND_CORS_ORIGINS"
```

The environment variable is not valid JSON. Use:

```txt
["https://checkly-hub.vercel.app"]
```

not:

```txt
https://checkly-hub.vercel.app
```

### Login request fails with `OPTIONS /api/auth/login 400 Bad Request`

This usually means CORS rejected the browser preflight request.

Check Render's `BACKEND_CORS_ORIGINS` and make sure it exactly matches the Vercel domain being used in the browser.

### Frontend cannot reach backend

Check Vercel's environment variable:

```txt
VITE_API_BASE_URL=https://<render-backend-domain>.onrender.com/api
```

The `/api` suffix is required.

### Logo or image missing in production

Images imported from `src/assets` should be imported in TypeScript/React files, not referenced as `/src/assets/...` paths.

Correct:

```tsx
import logo from '../assets/logo_cropped.png'

<img src={logo} alt="Checkly logo" />
```

Incorrect:

```tsx
<img src="/src/assets/logo_cropped.png" alt="Checkly logo" />
```

## Deployment order

A practical deployment order is:

1. Deploy the backend on Render.
2. Copy the Render backend URL.
3. Set `VITE_API_BASE_URL` in Vercel to the Render URL plus `/api`.
4. Deploy or redeploy the frontend on Vercel.
5. Copy the final Vercel frontend URL.
6. Set `BACKEND_CORS_ORIGINS` in Render to the Vercel origin.
7. Restart or redeploy the Render backend.

## Notes

Render free instances may sleep after inactivity. The first backend request after sleep can be slow.
