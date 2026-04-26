import os
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List

from database import get_db
from models import User, Tweet, Media, likes, followers_table
from schemas import (
    BaseResponse, TweetCreate, TweetListResponse,
    MediaResponse, UserProfile, UserShort, TweetResponse
)

router = APIRouter(prefix="/api")

async def get_current_user(api_key: str = Header(None), db: AsyncSession = Depends(get_db)):
    if not api_key:
        raise HTTPException(status_code=401, detail="api-key header missing")

    result = await db.execute(select(User).where(User.api_key == api_key))
    user = result.scalars().first()

    if not user:
        # В реальном проекте тут можно возвращать формат ErrorResponse из ТЗ
        raise HTTPException(status_code=401, detail="Invalid api-key")
    return user

# GET METHOD =======================================================================================

@router.get("/users/me")
async def get_my_profile(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение информации о своем профиле"""
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.followers), # Изменили с followers_ref на followers
            selectinload(User.following)
        )
        .where(User.id == current_user.id)
    )
    user = result.scalars().first()

    if not user:
         raise HTTPException(status_code=404, detail="User not found")

    return {
        "result": True,
        "user": {
            "id": int(user.id),
            "name": str(user.name),
            "followers": [{"id": int(f.id), "name": str(f.name)} for f in user.followers],
            "following": [{"id": int(f.id), "name": str(f.name)} for f in user.following]
        }
    }

@router.get("/users/{user_id}")
async def get_user_profile(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение информации о произвольном профиле"""
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.followers),
            selectinload(User.following)
        )
        .where(User.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "result": True,
        "user": {
            "id": int(user.id),
            "name": str(user.name),
            "followers": [{"id": int(f.id), "name": str(f.name)} for f in user.followers],
            "following": [{"id": int(f.id), "name": str(f.name)} for f in user.following]
        }
    }

@router.get("/tweets", response_model=TweetListResponse)
async def get_tweets(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получение ленты твитов"""
    result = await db.execute(
        select(Tweet).options(
            selectinload(Tweet.author),
            selectinload(Tweet.liked_by),
            selectinload(Tweet.attachments)
        ).order_by(Tweet.id.desc())
    )
    tweets_db = result.scalars().all()

    # Преобразуем в формат ответа
    tweets_res = []
    for t in tweets_db:
        tweets_res.append(TweetResponse(
            id=t.id,
            content=t.content,
            attachments=[m.file_path for m in t.attachments],
            author=UserShort.model_validate(t.author),
            likes=[UserShort.model_validate(u) for u in t.liked_by]
        ))

    return {"result": True, "tweets": tweets_res}

# POST METHOD =======================================================================================

@router.post("/medias", response_model=MediaResponse)
async def upload_media(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Загрузка изображения"""
    os.makedirs("static/images", exist_ok=True)
    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = f"static/images/{file_name}"

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    new_media = Media(file_path=f"/images/{file_name}")
    db.add(new_media)
    await db.commit()
    await db.refresh(new_media)

    return {"result": True, "media_id": new_media.id}


@router.post("/tweets", response_model=BaseResponse)
async def create_tweet(
        tweet_in: TweetCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Создание нового твита"""
    new_tweet = Tweet(content=tweet_in.tweet_data, author_id=current_user.id)
    db.add(new_tweet)
    await db.flush()  # Получаем ID твита до коммита

    if tweet_in.tweet_media_ids:
        result = await db.execute(
            select(Media).where(Media.id.in_(tweet_in.tweet_media_ids))
        )
        medias = result.scalars().all()
        for m in medias:
            m.tweet_id = new_tweet.id
    print(new_tweet.id*5)
    await db.commit()
    return {"result": True, "tweet_id":new_tweet.id}

@router.post("/tweets/{tweet_id}/likes", response_model=BaseResponse)
async def like_tweet(
        tweet_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Поставить лайк на твит"""
    # Загружаем твит вместе с его лайками
    result = await db.execute(
        select(Tweet).options(selectinload(Tweet.liked_by)).where(Tweet.id == tweet_id)
    )
    tweet = result.scalars().first()

    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    # Проверяем, не ставил ли пользователь лайк ранее
    if not any(u.id == current_user.id for u in tweet.liked_by):
        tweet.liked_by.append(current_user)
        await db.commit()

    return {"result": True}

@router.post("/users/{user_id}/follow", response_model=BaseResponse)
async def follow_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Подписаться на пользователя"""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    result = await db.execute(select(User).options(selectinload(User.followers)).where(User.id == user_id))
    user_to_follow = result.scalars().first()

    if not user_to_follow:
        raise HTTPException(status_code=404, detail="User not found")

    if not any(u.id == current_user.id for u in user_to_follow.followers):
        user_to_follow.followers.append(current_user)
        await db.commit()

    return {"result": True}

# DELETE METHOD =======================================================================================

@router.delete("/tweets/{tweet_id}/likes", response_model=BaseResponse)
async def unlike_tweet(
        tweet_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Убрать лайк с твита"""
    result = await db.execute(
        select(Tweet).options(selectinload(Tweet.liked_by)).where(Tweet.id == tweet_id)
    )
    tweet = result.scalars().first()

    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    # Ищем текущего пользователя в списке лайкнувших и удаляем
    user_to_remove = next((u for u in tweet.liked_by if u.id == current_user.id), None)
    if user_to_remove:
        tweet.liked_by.remove(user_to_remove)
        await db.commit()

    return {"result": True}

@router.delete("/tweets/{tweet_id}", response_model=BaseResponse)
async def delete_tweet(
        tweet_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Удаление твита (только своего)"""
    result = await db.execute(select(Tweet).where(Tweet.id == tweet_id))
    tweet = result.scalars().first()

    if not tweet:
        # В идеале возвращать ErrorResponse по ТЗ, но для простоты пока используем HTTPException
        raise HTTPException(status_code=404, detail="Tweet not found")

    if tweet.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own tweets")

    await db.delete(tweet)
    await db.commit()

    return {"result": True}

@router.delete("/users/{user_id}/follow", response_model=BaseResponse)
async def unfollow_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Отписаться от пользователя"""
    result = await db.execute(select(User).options(selectinload(User.followers)).where(User.id == user_id))
    user_to_unfollow = result.scalars().first()

    if not user_to_unfollow:
        raise HTTPException(status_code=404, detail="User not found")

    me = next((u for u in user_to_unfollow.followers if u.id == current_user.id), None)
    if me:
        user_to_unfollow.followers.remove(me)
        await db.commit()

    return {"result": True}
