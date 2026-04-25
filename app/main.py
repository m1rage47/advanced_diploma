import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api import router
from database import engine, Base

app = FastAPI(title="Twitter Clone API")
print("тут норм\n"*5)
# 1. Регистрируем API эндпоинты (ВАЖНО: они должны быть первыми)
app.include_router(router)
print("тут тоже\n"*5)
# 2. Создаем и подключаем папку для загруженных картинок
os.makedirs("static/images", exist_ok=True)
app.mount("/images", StaticFiles(directory="static/images"), name="images")
print("и тут\n"*5)
# 3. Подключаем папки со статикой фронтенда
app.mount("/js", StaticFiles(directory="../dist/js"), name="js")
app.mount("/css", StaticFiles(directory="../dist/css"), name="css")
print("и тут тоже\n"*5)
# 4. Отдаем иконку сайта
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("../dist/favicon.ico")

# 5. Catch-all роут для SPA (Single Page Application)
# Любой запрос, который не подошел под правила выше (например, переход в профиль),
# будет возвращать index.html, чтобы фронтенд сам разобрался, какую страницу показать.
@app.get("/{catchall:path}", include_in_schema=False)
async def serve_spa(catchall: str):
    # Проверяем, существует ли файл, чтобы не падала ошибка, если папки dist еще нет
    if os.path.exists("../dist/index.html"):
        return FileResponse("../dist/index.html")

    return {"error": "Frontend not found. Please put files in 'dist' folder."}

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)