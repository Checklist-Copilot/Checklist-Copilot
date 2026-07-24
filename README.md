# AI Checklist Copilot

A proof-of-concept checklist editor and runner with an AI copilot. The frontend is a Vite/React app and the backend is a FastAPI app.

## Local setup

### Environment files

Create/update the required environment files before starting the apps:

- Frontend: `frontend/checklist-copilot-frontend/.env`
  - Localhost only:
    ```env
    VITE_API_BASE_URL=http://127.0.0.1:8000/api
    ```
  - Accessible from a phone on the same local network: replace `<YOUR_COMPUTER_LAN_IP>` with your computer's local IP address:
    ```env
    VITE_API_BASE_URL=http://<YOUR_COMPUTER_LAN_IP>:8000/api
    ```
- Backend: `backend/.env` must exist and contain the required backend settings such as `DATABASE_URL` and `JWT_SECRET_KEY`.

## Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
fastapi dev app/main.py
```

To make the backend reachable from a phone on the same local network:

```bash
fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

## Run the frontend

```bash
cd frontend/checklist-copilot-frontend
npm ci
npm run dev
```

To make the frontend reachable from a phone on the same local network:

```bash
npm run dev -- --host 0.0.0.0
```

Then open the URL printed by Vite, for example `http://127.0.0.1:5173` locally or `http://<YOUR_COMPUTER_LAN_IP>:5173` from your phone.
