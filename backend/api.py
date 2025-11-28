from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.database import SessionLocal
from backend.search import SearchService
from backend.models import Channel, Video, Transcript, TranscriptError
from sqlalchemy import func
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YouTube Transcript Search API",
    description="Search through YouTube video transcripts",
    version="1.0.0"
)

# CORS configuration - allow all origins since it's your personal server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "YouTube Transcript Search API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/search",
            "channels": "/api/channels",
            "stats": "/api/stats"
        }
    }

@app.get("/api/search")
async def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    exact_match: bool = Query(False, description="Require exact phrase match"),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0, description="Minimum similarity score for fuzzy matches")
):
    """
    Search across video transcripts, titles, and descriptions.

    Returns results ranked by relevance with snippets and timestamps.
    """
    try:
        db = next(get_db())
        search_service = SearchService(db)

        results = search_service.search(
            query=q,
            limit=limit,
            exact_match=exact_match,
            min_similarity=min_similarity
        )

        return {
            "query": q,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/channels")
async def list_channels():
    """List all indexed channels"""
    try:
        db = next(get_db())

        channels = db.query(
            Channel,
            func.count(Video.id).label('video_count'),
            func.count(Transcript.id).label('transcript_count')
        ).outerjoin(
            Video, Channel.id == Video.channel_id
        ).outerjoin(
            Transcript, Video.id == Transcript.video_id
        ).group_by(Channel.id).all()

        result = []
        for channel, video_count, transcript_count in channels:
            result.append({
                "channel_id": channel.channel_id,
                "channel_name": channel.channel_name,
                "channel_url": channel.channel_url,
                "description": channel.description,
                "video_count": video_count,
                "transcript_count": transcript_count,
                "last_checked": channel.last_checked.isoformat() if channel.last_checked else None,
                "created_at": channel.created_at.isoformat()
            })

        return {"channels": result}
    except Exception as e:
        logger.error(f"Error listing channels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/channels/{channel_id}")
async def get_channel(channel_id: str):
    """Get details for a specific channel"""
    try:
        db = next(get_db())

        channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()

        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        videos = db.query(Video).filter(Video.channel_id == channel.id).all()

        videos_data = []
        for video in videos:
            has_transcript = db.query(Transcript).filter(Transcript.video_id == video.id).first() is not None
            errors = db.query(TranscriptError).filter(TranscriptError.video_id == video.id).all()

            videos_data.append({
                "video_id": video.video_id,
                "title": video.title,
                "published_at": video.published_at.isoformat(),
                "thumbnail_url": video.thumbnail_url,
                "has_transcript": has_transcript,
                "errors": [{"type": e.error_type, "message": e.error_message} for e in errors]
            })

        return {
            "channel_id": channel.channel_id,
            "channel_name": channel.channel_name,
            "channel_url": channel.channel_url,
            "description": channel.description,
            "last_checked": channel.last_checked.isoformat() if channel.last_checked else None,
            "videos": videos_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get overall statistics"""
    try:
        db = next(get_db())

        channel_count = db.query(Channel).count()
        video_count = db.query(Video).count()
        transcript_count = db.query(Transcript).count()
        error_count = db.query(TranscriptError).count()

        # Get error breakdown
        error_breakdown = db.query(
            TranscriptError.error_type,
            func.count(TranscriptError.id).label('count')
        ).group_by(TranscriptError.error_type).all()

        errors_by_type = {error_type: count for error_type, count in error_breakdown}

        return {
            "channels": channel_count,
            "videos": video_count,
            "transcripts": transcript_count,
            "coverage": f"{(transcript_count / video_count * 100):.1f}%" if video_count > 0 else "0%",
            "errors": error_count,
            "errors_by_type": errors_by_type
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        db = next(get_db())
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}