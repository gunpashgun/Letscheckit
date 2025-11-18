"""Pydantic models for Apify JSON reel data."""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, HttpUrl, Field


class MusicInfo(BaseModel):
    artist_name: Optional[str] = None
    song_name: Optional[str] = None
    audio_id: Optional[str] = None


class ApifyReel(BaseModel):
    """Model for a single reel from Apify JSON."""
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
    inputUrl: Optional[HttpUrl] = None
    displayUrl: Optional[HttpUrl] = None
    images: Optional[List[str]] = Field(default_factory=list)
    firstComment: Optional[str] = None
    latestComments: Optional[List[Dict[str, Any]]] = Field(default_factory=list)  # массив объектов
    taggedUsers: Optional[List[Dict[str, Any]]] = Field(default_factory=list)  # массив объектов
    musicInfo: Optional[MusicInfo] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }

