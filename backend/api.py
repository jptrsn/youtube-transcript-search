from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.search import SearchService
from backend.models import Channel, Video, Transcript, TranscriptError
from backend.services.channel_service import ChannelService
from backend.youtube_client import YouTubeClient
from sqlalchemy import func
from typing import Optional, Dict
import logging
import asyncio
import json
import uuid
import queue
from datetime import datetime, timezone
from backend.youtube_client import YouTubeClient
from backend.services.websub_service import WebSubService
from fastapi import Request
from contextlib import asynccontextmanager
from backend.scheduler import start_scheduler, shutdown_scheduler

import sys

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger("backend.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down application...")
    shutdown_scheduler()

app = FastAPI(
    title="YouTube Transcript Search API",
    description="Search through YouTube video transcripts",
    version="1.0.0",
    lifespan=lifespan
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
    min_similarity: float = Query(0.3, ge=0.0, le=1.0, description="Minimum similarity score for fuzzy matches"),
    db: Session = Depends(get_db)
):
    """
    Search across video transcripts, titles, and descriptions.

    Returns results ranked by relevance with snippets and timestamps.
    """
    try:

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
async def list_channels(db: Session = Depends(get_db)):
    """List all indexed channels"""
    try:
        from sqlalchemy import select

        # Subquery for video counts
        video_counts = select(
            Video.channel_id,
            func.count(Video.id).label('video_count')
        ).group_by(Video.channel_id).subquery()

        # Subquery for transcript counts
        transcript_counts = select(
            Video.channel_id,
            func.count(Transcript.id).label('transcript_count')
        ).join(
            Transcript, Video.id == Transcript.video_id
        ).group_by(Video.channel_id).subquery()

        # Main query
        channels = db.query(
            Channel,
            func.coalesce(video_counts.c.video_count, 0).label('video_count'),
            func.coalesce(transcript_counts.c.transcript_count, 0).label('transcript_count')
        ).outerjoin(
            video_counts, Channel.id == video_counts.c.channel_id
        ).outerjoin(
            transcript_counts, Channel.id == transcript_counts.c.channel_id
        ).all()

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
async def get_channel(channel_id: str, db: Session = Depends(get_db)):
    """Get details for a specific channel"""
    try:

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
async def get_stats(db: Session = Depends(get_db)):
    """Get overall statistics"""
    try:

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
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}

@app.post("/api/channels/add")
async def add_channel(channel_url: str = Query(..., description="YouTube channel URL"), db: Session = Depends(get_db)):
    """
    Add a new channel and fetch all its videos/transcripts.
    This is a synchronous endpoint - use WebSocket for real-time progress.
    """
    try:
        service = ChannelService(db)
        result = service.add_or_update_channel(channel_url)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding channel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/channels/{channel_id}/check-new-async")
async def check_new_videos_async(
    background_tasks: BackgroundTasks,
    channel_id: str
):
    """Check for new videos in an existing channel asynchronously"""
    job_id = str(uuid.uuid4())
    db = SessionLocal()

    logger.info(f"Starting check_new job {job_id} for channel {channel_id}")

    background_tasks.add_task(
        run_channel_job,
        job_id=job_id,
        operation='check_new',
        db=db,
        channel_id=channel_id
    )

    return {
        'job_id': job_id,
        'websocket_url': f'/ws/channel-job/{job_id}'
    }

@app.post("/api/channels/{channel_id}/retry-failed")
async def retry_failed(channel_id: str, db: Session = Depends(get_db)):
    """Retry fetching transcripts for videos that failed"""
    try:
        service = ChannelService(db)
        result = service.retry_failed_transcripts(channel_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrying failed transcripts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket connection manager with message queue
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.message_queues: Dict[str, queue.Queue] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[job_id] = websocket
        self.message_queues[job_id] = queue.Queue()

    def disconnect(self, job_id: str):
        if job_id in self.active_connections:
            del self.active_connections[job_id]
        if job_id in self.message_queues:
            del self.message_queues[job_id]

    def queue_message(self, job_id: str, message: dict):
        """Queue a message to be sent (thread-safe)"""
        if job_id in self.message_queues:
            self.message_queues[job_id].put(message)

    async def send_queued_messages(self, job_id: str):
        """Send all queued messages for a job"""
        if job_id not in self.message_queues or job_id not in self.active_connections:
            return

        try:
            while not self.message_queues[job_id].empty():
                message = self.message_queues[job_id].get_nowait()
                await self.active_connections[job_id].send_json(message)
        except Exception as e:
            logger.error(f"Error sending queued messages: {e}")

manager = ConnectionManager()

def create_progress_callback(job_id: str):
    """Create a progress callback that queues updates"""
    def callback(event: str, data: dict):
        manager.queue_message(job_id, {
            'event': event,
            'data': data
        })

    return callback

def run_channel_job(job_id: str, operation: str, db: Session, **kwargs):
    """Run a channel operation in the background with progress updates"""
    logger.info(f"run_channel_job STARTED: job_id={job_id}, operation={operation}, kwargs={kwargs}")
    try:
        callback = create_progress_callback(job_id)
        service = ChannelService(db, progress_callback=callback)

        logger.info(f"About to execute operation: {operation}")

        if operation == 'add_channel':
            service.add_or_update_channel(kwargs['channel_url'])
        elif operation == 'add_channel_limited':
            service.add_channel_with_limited_transcripts(kwargs['channel_url'], kwargs.get('transcript_limit', 5))
        elif operation == 'check_new':
            service.check_for_new_videos(kwargs['channel_id'])
        elif operation == 'retry_failed':
            service.retry_failed_transcripts(kwargs['channel_id'])
        elif operation == 'fetch_missing':
            logger.info(f"Calling fetch_missing_transcripts for channel {kwargs['channel_id']}")
            service.fetch_missing_transcripts(kwargs['channel_id'], kwargs.get('limit'))

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        callback('error', {'message': str(e)})
    finally:
        db.close()

@app.websocket("/ws/channel-job/{job_id}")
async def websocket_channel_job(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time channel operation updates"""
    await manager.connect(job_id, websocket)
    try:
        while True:
            # Send any queued messages
            await manager.send_queued_messages(job_id)

            # Keep connection alive with small delay
            await asyncio.sleep(0.1)

            # Also listen for ping from client
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(job_id)

@app.post("/api/channels/add-async")
async def add_channel_async(
    background_tasks: BackgroundTasks,
    channel_url: str = Query(..., description="YouTube channel URL")
):
    """
    Add a new channel asynchronously with WebSocket progress updates.
    Returns a job_id to connect to via WebSocket.
    """
    job_id = str(uuid.uuid4())
    db = SessionLocal()

    # Start background task
    background_tasks.add_task(
        run_channel_job,
        job_id=job_id,
        operation='add_channel',
        db=db,
        channel_url=channel_url
    )

    return {
        'job_id': job_id,
        'websocket_url': f'/ws/channel-job/{job_id}'
    }

@app.post("/api/channels/{channel_id}/check-new-async")
async def check_new_videos_async(
    background_tasks: BackgroundTasks,
    channel_id: str
):
    """Check for new videos asynchronously with WebSocket progress updates"""
    job_id = str(uuid.uuid4())
    db = SessionLocal()

    background_tasks.add_task(
        run_channel_job,
        job_id=job_id,
        operation='check_new',
        db=db,
        channel_id=channel_id
    )

    return {
        'job_id': job_id,
        'websocket_url': f'/ws/channel-job/{job_id}'
    }

@app.post("/api/channels/{channel_id}/retry-failed-async")
async def retry_failed_async(
    background_tasks: BackgroundTasks,
    channel_id: str
):
    """Retry failed transcripts asynchronously"""
    job_id = str(uuid.uuid4())
    db = SessionLocal()

    logger.info(f"Starting retry_failed job {job_id} for channel {channel_id}")

    background_tasks.add_task(
        run_channel_job,
        job_id=job_id,
        operation='retry_failed',
        db=db,
        channel_id=channel_id
    )

    return {
        'job_id': job_id,
        'websocket_url': f'/ws/channel-job/{job_id}'
    }

@app.get("/api/channels/{channel_id}/details")
async def get_channel_details(channel_id: str, db: Session = Depends(get_db)):
    """Get detailed channel information including video list"""
    try:
        channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()

        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        # Single query with joins - fetch everything at once
        from sqlalchemy.orm import joinedload

        videos = db.query(Video).filter(
            Video.channel_id == channel.id
        ).options(
            joinedload(Video.transcript),
            joinedload(Video.transcript_errors)
        ).order_by(Video.published_at.desc()).all()

        videos_data = []
        for video in videos:
            videos_data.append({
                "video_id": video.video_id,
                "title": video.title,
                "description": video.description,
                "published_at": video.published_at.isoformat(),
                "thumbnail_url": video.thumbnail_url,
                "has_transcript": video.transcript is not None,
                "errors": [{"type": e.error_type, "message": e.error_message} for e in video.transcript_errors]
            })

        return {
            "channel_id": channel.channel_id,
            "channel_name": channel.channel_name,
            "channel_url": channel.channel_url,
            "description": channel.description,
            "last_checked": channel.last_checked.isoformat() if channel.last_checked else None,
            "video_count": len(videos),
            "transcript_count": sum(1 for v in videos_data if v["has_transcript"]),
            "videos": videos_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channel details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/channels/{channel_id}/search")
async def search_channel(
    channel_id: str,
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=200, description="Results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """Search within a specific channel's transcripts with pagination"""
    try:
        search_service = SearchService(db)
        results, total_count = search_service.search_channel(
            channel_id=channel_id,
            query=q,
            limit=limit,
            offset=offset
        )

        return {
            "query": q,
            "channel_id": channel_id,
            "count": len(results),
            "total": total_count,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(results) < total_count,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error searching channel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/channels/add-limited-async")
async def add_channel_limited_async(
    background_tasks: BackgroundTasks,
    channel_url: str = Query(..., description="YouTube channel URL"),
    transcript_limit: int = Query(5, ge=1, le=20, description="Number of transcripts to fetch")
):
    """
    Add a new channel with limited transcript fetching (for auto-add feature).
    Fetches all video metadata but only transcripts for first N videos.
    """
    job_id = str(uuid.uuid4())
    db = SessionLocal()

    background_tasks.add_task(
        run_channel_job,
        job_id=job_id,
        operation='add_channel_limited',
        db=db,
        channel_url=channel_url,
        transcript_limit=transcript_limit
    )

    return {
        'job_id': job_id,
        'websocket_url': f'/ws/channel-job/{job_id}'
    }

@app.post("/api/channels/{channel_id}/fetch-missing-async")
async def fetch_missing_async(
    background_tasks: BackgroundTasks,
    channel_id: str,
    limit: Optional[int] = Query(None, ge=1, le=100, description="Limit number of videos to process")
):
    """Fetch transcripts for videos that haven't been attempted yet"""
    job_id = str(uuid.uuid4())
    db = SessionLocal()

    logger.info(f"Starting fetch_missing job {job_id} for channel {channel_id}")

    background_tasks.add_task(
        run_channel_job,
        job_id=job_id,
        operation='fetch_missing',
        db=db,
        channel_id=channel_id,
        limit=limit
    )

    return {
        'job_id': job_id,
        'websocket_url': f'/ws/channel-job/{job_id}'
    }

@app.get("/api/channels/resolve-handle/{handle}")
async def resolve_handle(handle: str):
    """Resolve a YouTube handle (@username) to channel ID"""
    try:
        youtube_client = YouTubeClient()
        channel_id = youtube_client.resolve_handle(handle)

        if not channel_id:
            raise HTTPException(status_code=404, detail="Channel not found")

        return {
            "handle": handle,
            "channel_id": channel_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving handle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{video_id}/exists")
async def check_video_exists(video_id: str, db: Session = Depends(get_db)):
    """Check if a video exists in the database"""
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()

        if video:
            # Check if it has a transcript
            has_transcript = db.query(Transcript).filter(
                Transcript.video_id == video.id
            ).first() is not None

            return {"exists": True, "has_transcript": has_transcript}
        else:
            return {"exists": False, "has_transcript": False}

    except Exception as e:
        logger.error(f"Error checking video exists: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/videos/submit")
async def submit_video_transcript(
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Submit a video and its transcript from the browser extension"""
    try:
        data = await request.json()
        video_data = data.get('video')
        transcript_data = data.get('transcript')

        if not video_data or not transcript_data:
            raise HTTPException(status_code=400, detail="Missing video or transcript data")

        # Check if channel exists
        channel = db.query(Channel).filter(
            Channel.channel_id == video_data['channelId']
        ).first()

        is_new_channel = channel is None

        if not channel:
            # Create minimal channel entry
            youtube_client = YouTubeClient()
            channel_info = youtube_client.get_channel_info(video_data['channelId'])

            if not channel_info:
                raise HTTPException(status_code=400, detail="Could not fetch channel info")

            channel = Channel(
                channel_id=channel_info['channel_id'],
                channel_name=channel_info['channel_name'],
                channel_url=f"https://www.youtube.com/channel/{channel_info['channel_id']}",
                description=channel_info.get('description', ''),
                last_checked=datetime.now(timezone.utc)
            )
            db.add(channel)
            db.commit()
            db.refresh(channel)

        # Check if video already exists
        existing_video = db.query(Video).filter(
            Video.video_id == video_data['videoId']
        ).first()

        if existing_video:
            # Check if it has a transcript
            existing_transcript = db.query(Transcript).filter(
                Transcript.video_id == existing_video.id
            ).first()

            if existing_transcript:
                return {"success": True, "message": "Video already has transcript"}

        # Create video entry if it doesn't exist
        if not existing_video:
            video = Video(
                video_id=video_data['videoId'],
                channel_id=channel.id,
                title=video_data['title'],
                description=video_data.get('description', ''),
                published_at=datetime.fromisoformat(video_data['publishedAt'].replace('Z', '+00:00')),
                thumbnail_url=video_data.get('thumbnailUrl', '')
            )
            db.add(video)
            db.commit()
            db.refresh(video)
        else:
            video = existing_video

        # Create transcript
        full_text = ' '.join([seg['text'] for seg in transcript_data])

        transcript = Transcript(
            video_id=video.id,
            text=full_text,
            snippets=transcript_data,
            language_code='en',
            is_generated=False
        )
        db.add(transcript)
        db.commit()

        logger.info(f"Submitted transcript for video {video_data['videoId']} from extension")

        # If this was a new channel, trigger async full channel indexing
        if is_new_channel:
            logger.info(f"New channel detected, triggering async channel indexing for {channel.channel_id}")
            channel_url = f"https://www.youtube.com/channel/{channel.channel_id}"

            # Trigger background task to add all videos from channel
            background_tasks.add_task(
                run_channel_job,
                job_id=str(uuid.uuid4()),
                operation='add_channel',
                db=SessionLocal(),
                channel_url=channel_url
            )

        return {"success": True, "message": "Transcript submitted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/videos/batch-snippets")
async def batch_get_snippets(request: Request, db: Session = Depends(get_db)):
    """
    Get best snippets for multiple videos in one request.
    Accepts: { video_ids: [...], query: "search term" }
    Returns: { video_id: { snippet, timestamp }, ... }
    """
    try:
        data = await request.json()
        video_ids = data.get('video_ids', [])
        query = data.get('query', '')

        if not video_ids or not query:
            raise HTTPException(status_code=400, detail="video_ids and query required")

        search_service = SearchService(db)
        results = search_service.get_batch_snippets(video_ids, query)

        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch snippets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{video_id}/details")
async def get_video_details(
    video_id: str,
    q: str = Query(None, description="Optional search query to highlight matches"),
    db: Session = Depends(get_db)
):
    """Get video details with optional search matches or full transcript"""
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()

        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        channel = db.query(Channel).filter(Channel.id == video.channel_id).first()
        transcript = db.query(Transcript).filter(Transcript.video_id == video.id).first()

        response = {
            "video_id": video.video_id,
            "title": video.title,
            "description": video.description,
            "published_at": video.published_at.isoformat(),
            "thumbnail_url": video.thumbnail_url,
            "channel": {
                "channel_id": channel.channel_id,
                "channel_name": channel.channel_name,
                "channel_url": channel.channel_url
            },
            "has_transcript": transcript is not None
        }

        if transcript:
            # If there's a search query, find all matches
            if q:
                search_service = SearchService(db)
                matches = search_service.get_all_video_matches(video.video_id, q)
                response["matches"] = matches
                response["match_count"] = len(matches)
            else:
                # No search query - return full transcript with timestamps
                response["transcript"] = transcript.snippets

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add these imports at the top of the file
from backend.services.websub_service import WebSubService
from fastapi import Request

# Add these endpoints (I'll put them after your existing channel endpoints)

@app.post("/api/webhooks/youtube")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive WebSub notifications from YouTube.
    This is called by YouTube's PubSubHubbub hub when a video is uploaded/updated.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Get signature from headers
        signature = request.headers.get('X-Hub-Signature')

        # Process the notification
        websub_service = WebSubService(db)
        result = websub_service.process_notification(body, signature)

        if result['success']:
            logger.info(f"WebSub notification processed: {result['message']}")
            return {"success": True, "message": result['message']}
        else:
            logger.warning(f"WebSub notification failed: {result['message']}")
            return {"success": False, "message": result['message']}, 400

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/webhooks/youtube")
async def verify_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verify WebSub subscription requests from YouTube hub.
    The hub sends a GET request with challenge to verify our endpoint.
    """
    try:
        # Get query parameters
        mode = request.query_params.get('hub.mode')
        topic = request.query_params.get('hub.topic')
        challenge = request.query_params.get('hub.challenge')
        verify_token = request.query_params.get('hub.verify_token')
        lease_seconds = request.query_params.get('hub.lease_seconds')

        if not all([mode, topic, challenge, verify_token]):
            raise HTTPException(status_code=400, detail="Missing required parameters")

        # Convert lease_seconds to int if present
        lease_seconds_int = int(lease_seconds) if lease_seconds else None

        # Verify the subscription
        websub_service = WebSubService(db)
        success, response_challenge = websub_service.verify_subscription(
            mode=mode,
            topic=topic,
            challenge=challenge,
            verify_token=verify_token,
            lease_seconds=lease_seconds_int
        )

        if success and response_challenge:
            logger.info(f"WebSub verification successful for topic: {topic}")
            # Must return the challenge as plain text
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(content=response_challenge)
        else:
            logger.warning(f"WebSub verification failed for topic: {topic}")
            raise HTTPException(status_code=404, detail="Verification failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during webhook verification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/channels/{channel_id}/websub/subscribe")
async def subscribe_channel_websub(channel_id: str, db: Session = Depends(get_db)):
    """
    Manually subscribe to WebSub notifications for a channel.
    Useful for subscribing to existing channels or resubscribing after failures.
    """
    try:
        websub_service = WebSubService(db)
        result = websub_service.subscribe_to_channel(channel_id)

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error subscribing to channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/channels/{channel_id}/websub/unsubscribe")
async def unsubscribe_channel_websub(channel_id: str, db: Session = Depends(get_db)):
    """
    Unsubscribe from WebSub notifications for a channel.
    """
    try:
        websub_service = WebSubService(db)
        result = websub_service.unsubscribe_from_channel(channel_id)

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error unsubscribing from channel {channel_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/channels/{channel_id}/websub/status")
async def get_channel_websub_status(channel_id: str, db: Session = Depends(get_db)):
    """
    Get WebSub subscription status for a specific channel.
    """
    try:
        websub_service = WebSubService(db)
        status = websub_service.get_subscription_status(channel_id)

        if status:
            return status
        else:
            return {"subscribed": False, "message": "No active subscription"}

    except Exception as e:
        logger.error(f"Error getting subscription status for {channel_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/websub/subscriptions")
async def list_websub_subscriptions(db: Session = Depends(get_db)):
    """
    List all WebSub subscriptions with their status.
    Useful for monitoring and debugging.
    """
    try:
        websub_service = WebSubService(db)
        subscriptions = websub_service.list_all_subscriptions()

        return {
            "total": len(subscriptions),
            "subscriptions": subscriptions
        }

    except Exception as e:
        logger.error(f"Error listing subscriptions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/websub/renew")
async def renew_expiring_subscriptions(
    hours_before_expiry: int = Query(24, ge=1, le=168, description="Renew subscriptions expiring within this many hours"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger renewal of expiring subscriptions.
    This will normally run via scheduled job, but can be triggered manually.
    """
    try:
        websub_service = WebSubService(db)
        result = websub_service.renew_expiring_subscriptions(hours_before_expiry)

        return result

    except Exception as e:
        logger.error(f"Error renewing subscriptions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))