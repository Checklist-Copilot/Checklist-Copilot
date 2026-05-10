from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.checklists.router import router as checklists_router
from app.ai.router import router as ai_router
from app.images.router import router as images_router

app = FastAPI(title="AI Checklist Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(checklists_router, prefix="/api/checklists", tags=["checklists"])
app.include_router(ai_router, prefix="/api/ai", tags=["ai"])
app.include_router(images_router, prefix="/api/images", tags=["images"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
