"""Pydantic models for Apify Instagram Reel JSON."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, Field


class MusicInfo(BaseModel):
    """Music information from Apify."""
    artist_name: Optional[str] = None
    song_name: Optional[str] = None
    audio_id: Optional[str] = None


class ApifyReel(BaseModel):
    """Main model for Instagram reel from Apify."""
    id: str
    type: Optional[str] = None
    shortCode: str
    caption: Optional[str] = None
    hashtags: List[str] = Field(default_factory=list)
    url: HttpUrl
    videoUrl: HttpUrl
    audioUrl: Optional[HttpUrl] = None
    likesCount: int = 0
    commentsCount: int = 0
    videoViewCount: Optional[int] = None
    videoPlayCount: Optional[int] = None
    timestamp: datetime
    ownerFullName: str
    ownerUsername: str
    ownerId: str
    productType: Optional[str] = None
    videoDuration: float
    inputUrl: Optional[str] = None
    displayUrl: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    firstComment: Optional[str] = None
    latestComments: List[str] = Field(default_factory=list)
    taggedUsers: List[str] = Field(default_factory=list)
    musicInfo: Optional[MusicInfo] = None
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }

