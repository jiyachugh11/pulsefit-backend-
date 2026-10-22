from pathlib import Path
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')

from app.routes import users, devices, challenges, metadata, telemetry, social, leaderboard

app = FastAPI(title='PulseFit', description='Five databases. One fitness application.')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
templates = Jinja2Templates(directory=ROOT / 'app' / 'templates')
for module in (users, devices, challenges, metadata, telemetry, social, leaderboard):
    app.include_router(module.router)


@app.get('/', include_in_schema=False)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name='index.html',
        context={'telemetry_day': os.getenv('TELEMETRY_DEFAULT_DAY', '2026-10-11')})
