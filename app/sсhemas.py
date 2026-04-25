from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class BaseResponse(BaseModel):
    result: bool = True
    tweet_id: Optional[int]

class UserShort(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class UserProfile(UserShort):
    followers: List[UserShort]
    following: List[UserShort]

class TweetCreate(BaseModel):
    tweet_data: str
    tweet_media_ids: Optional[List[int]] = None

class TweetResponse(BaseModel):
    id: int
    content: str
    attachments: List[str]
    author: UserShort
    likes: List[UserShort]

    model_config = ConfigDict(from_attributes=True)

class TweetListResponse(BaseResponse):
    tweets: List[TweetResponse]

class MediaResponse(BaseResponse):
    media_id: int


class ErrorResponse(BaseModel):
    result: bool = False
    error_type: str
    error_message: str