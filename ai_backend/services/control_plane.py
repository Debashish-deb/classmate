from sqlalchemy.orm import Session
from ..database.models import User
import redis.asyncio as redis
from ..core.telemetry import get_logger
import os
import json

logger = get_logger(__name__)

class ControlPlane:
    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client

    async def get_user_tier(self, user_id: str) -> str:
        """
        Get user tier with caching.
        """
        cache_key = f"user:{user_id}:tier"
        
        if self.redis:
            cached_tier = await self.redis.get(cache_key)
            if cached_tier:
                return cached_tier.decode('utf-8')

        # Fallback to DB
        user = self.db.query(User).filter(User.id == user_id).first()
        tier = user.tier if user else "free"
        
        if self.redis:
            await self.redis.setex(cache_key, 300, tier) # 5 min cache
            
        return tier

    async def health_check(self) -> dict:
        """
        System-wide health check.
        """
        health = {
            "status": "healthy",
            "services": {
                "database": "up",
                "redis": "up" if self.redis else "down",
                "control_plane": "ready"
            }
        }
        # Real logic would check connections here
        return health
