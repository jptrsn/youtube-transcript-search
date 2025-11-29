from datetime import datetime
from sqlalchemy.orm import Session
from backend.models import Channel, Video, Transcript, TranscriptError
from backend.youtube_client import YouTubeClient
from backend.transcript_fetcher import TranscriptFetcher, IpBlockedException
from typing import Callable, Optional, Dict, Any

class ChannelService:
    def __init__(self, db: Session, progress_callback: Optional[Callable] = None):
        self.db = db
        self.yt_client = YouTubeClient()
        self.transcript_fetcher = TranscriptFetcher()
        self.progress_callback = progress_callback or self._default_progress

    def _default_progress(self, event: str, data: Dict[str, Any]):
        """Default progress callback that does nothing"""
        pass

    def _emit(self, event: str, data: Dict[str, Any]):
        """Emit a progress event"""
        self.progress_callback(event, data)

    def add_or_update_channel(self, channel_url: str) -> Dict[str, Any]:
        """
        Add a new channel or update an existing one.
        Returns summary statistics.
        """
        try:
            self._emit('status', {'message': f'Extracting channel ID from URL: {channel_url}'})
            channel_id = self.yt_client.extract_channel_id(channel_url)

            if not channel_id:
                raise ValueError('Could not extract channel ID from URL')

            self._emit('channel_id_extracted', {'channel_id': channel_id})

            # Get channel info
            self._emit('status', {'message': 'Fetching channel information...'})
            channel_info = self.yt_client.get_channel_info(channel_id)

            if not channel_info:
                raise ValueError('Could not fetch channel information')

            self._emit('channel_info', {
                'channel_name': channel_info['channel_name'],
                'description': channel_info['description'][:100] + '...' if len(channel_info['description']) > 100 else channel_info['description']
            })

            # Check if channel exists
            existing_channel = self.db.query(Channel).filter(
                Channel.channel_id == channel_id
            ).first()

            if existing_channel:
                self._emit('status', {'message': f'Updating existing channel: {existing_channel.channel_name}'})
                existing_channel.channel_name = channel_info['channel_name']
                existing_channel.description = channel_info['description']
                existing_channel.last_checked = datetime.utcnow()
                existing_channel.updated_at = datetime.utcnow()
                db_channel = existing_channel
            else:
                self._emit('status', {'message': f'Adding new channel: {channel_info["channel_name"]}'})
                db_channel = Channel(
                    channel_id=channel_id,
                    channel_name=channel_info['channel_name'],
                    channel_url=channel_url,
                    description=channel_info['description'],
                    last_checked=datetime.utcnow()
                )
                self.db.add(db_channel)

            self.db.commit()
            self.db.refresh(db_channel)

            # Fetch all videos
            self._emit('status', {'message': 'Fetching all videos from channel...'})
            videos = self.yt_client.get_all_videos(channel_info['uploads_playlist_id'])

            self._emit('videos_found', {'count': len(videos)})

            # Process videos
            return self._process_videos(db_channel, videos)

        except Exception as e:
            self._emit('error', {'message': str(e)})
            raise

    def _process_videos(self, channel: Channel, videos: list) -> Dict[str, Any]:
        """Process videos and fetch transcripts"""
        new_videos = 0
        updated_videos = 0
        new_transcripts = 0
        stopped_early = False

        for idx, video_data in enumerate(videos, 1):
            video_id = video_data['video_id']

            self._emit('video_progress', {
                'current': idx,
                'total': len(videos),
                'video_id': video_id,
                'title': video_data['title']
            })

            # Check if video exists
            existing_video = self.db.query(Video).filter(
                Video.video_id == video_id
            ).first()

            if existing_video:
                updated_videos += 1
                db_video = existing_video
            else:
                db_video = Video(
                    channel_id=channel.id,
                    video_id=video_id,
                    title=video_data['title'],
                    description=video_data['description'],
                    published_at=datetime.fromisoformat(video_data['published_at'].replace('Z', '+00:00')),
                    thumbnail_url=video_data['thumbnail_url']
                )
                self.db.add(db_video)
                self.db.commit()
                self.db.refresh(db_video)
                new_videos += 1

            # Check if transcript exists
            existing_transcript = self.db.query(Transcript).filter(
                Transcript.video_id == db_video.id
            ).first()

            if existing_transcript:
                self._emit('video_status', {'status': 'has_transcript'})
                continue

            # Fetch transcript
            self._emit('video_status', {'status': 'fetching_transcript'})

            try:
                transcript_data, error_data = self.transcript_fetcher.fetch_transcript(video_id)
            except IpBlockedException as e:
                self._emit('error', {
                    'message': f'IP blocked after processing {idx} videos. Stopping transcript fetching.'
                })
                stopped_early = True
                break

            if transcript_data:
                db_transcript = Transcript(
                    video_id=db_video.id,
                    text=transcript_data['text'],
                    snippets=transcript_data['snippets'],
                    language_code=transcript_data['language_code'],
                    is_generated=transcript_data['is_generated']
                )
                self.db.add(db_transcript)
                self.db.commit()
                new_transcripts += 1
                self._emit('video_status', {
                    'status': 'transcript_saved',
                    'length': len(transcript_data['text'])
                })
            elif error_data:
                db_error = TranscriptError(
                    video_id=db_video.id,
                    error_type=error_data['error_type'],
                    error_message=error_data['error_message']
                )
                self.db.add(db_error)
                self.db.commit()
                self._emit('video_status', {
                    'status': 'error',
                    'error_type': error_data['error_type']
                })

        # Update channel last_checked
        channel.last_checked = datetime.utcnow()
        self.db.commit()

        summary = {
            'channel_name': channel.channel_name,
            'total_videos': len(videos),
            'new_videos': new_videos,
            'updated_videos': updated_videos,
            'new_transcripts': new_transcripts,
            'stopped_early': stopped_early
        }

        self._emit('complete', summary)

        return summary

    def check_for_new_videos(self, channel_id: str) -> Dict[str, Any]:
        """Check for new videos in an existing channel"""
        channel = self.db.query(Channel).filter(
            Channel.channel_id == channel_id
        ).first()

        if not channel:
            raise ValueError('Channel not found')

        self._emit('status', {'message': f'Checking for new videos: {channel.channel_name}'})

        # Get existing video IDs
        existing_video_ids = set(
            v.video_id for v in self.db.query(Video).filter(
                Video.channel_id == channel.id
            ).all()
        )

        # Fetch all videos from YouTube
        channel_info = self.yt_client.get_channel_info(channel.channel_id)
        all_videos = self.yt_client.get_all_videos(channel_info['uploads_playlist_id'])

        # Filter to only new videos
        new_videos = [v for v in all_videos if v['video_id'] not in existing_video_ids]

        self._emit('new_videos_found', {'count': len(new_videos)})

        if not new_videos:
            return {
                'channel_name': channel.channel_name,
                'new_videos': 0,
                'new_transcripts': 0
            }

        return self._process_videos(channel, new_videos)

    def retry_failed_transcripts(self, channel_id: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Retry fetching transcripts for videos that failed"""
        channel = self.db.query(Channel).filter(
            Channel.channel_id == channel_id
        ).first()

        if not channel:
            raise ValueError('Channel not found')

        self._emit('status', {'message': f'Retrying failed transcripts: {channel.channel_name}'})

        # Get videos without transcripts but with retryable errors
        RETRYABLE_ERRORS = {'RequestBlocked', 'IpBlocked', 'YouTubeRequestFailed'}

        videos_with_errors = self.db.query(TranscriptError.video_id).filter(
            TranscriptError.error_type.in_(RETRYABLE_ERRORS)
        ).distinct().subquery()

        query = self.db.query(Video).outerjoin(Transcript).filter(
            Video.channel_id == channel.id,
            Transcript.id == None,
            Video.id.in_(videos_with_errors)
        )

        # Add limit if specified
        if limit:
            query = query.limit(limit)

        videos_to_retry = query.all()

        self._emit('videos_to_retry', {'count': len(videos_to_retry)})

        success_count = 0
        stopped_early = False

        for idx, video in enumerate(videos_to_retry, 1):
            self._emit('video_progress', {
                'current': idx,
                'total': len(videos_to_retry),
                'video_id': video.video_id,
                'title': video.title
            })

            try:
                transcript_data, error_data = self.transcript_fetcher.fetch_transcript(video.video_id)
            except IpBlockedException as e:
                self._emit('error', {
                    'message': f'IP blocked after processing {idx} videos. Stopping transcript fetching.'
                })
                stopped_early = True
                break

            if transcript_data:
                db_transcript = Transcript(
                    video_id=video.id,
                    text=transcript_data['text'],
                    snippets=transcript_data['snippets'],
                    language_code=transcript_data['language_code'],
                    is_generated=transcript_data['is_generated']
                )
                self.db.add(db_transcript)

                # Delete previous errors
                self.db.query(TranscriptError).filter(
                    TranscriptError.video_id == video.id
                ).delete()

                self.db.commit()
                success_count += 1
                self._emit('video_status', {
                    'status': 'transcript_saved',
                    'length': len(transcript_data['text'])
                })
            elif error_data:
                # Update error
                db_error = TranscriptError(
                    video_id=video.id,
                    error_type=error_data['error_type'],
                    error_message=error_data['error_message']
                )
                self.db.add(db_error)
                self.db.commit()
                self._emit('video_status', {
                    'status': 'error',
                    'error_type': error_data['error_type']
                })

        summary = {
            'channel_name': channel.channel_name,
            'videos_processed': len(videos_to_retry) if not stopped_early else idx,
            'new_transcripts': success_count,
            'stopped_early': stopped_early
        }

        self._emit('complete', summary)

        return summary

    def add_channel_with_limited_transcripts(self, channel_url: str, transcript_limit: int = 5) -> Dict[str, Any]:
        """
        Add a new channel with limited transcript fetching (for auto-add feature).
        Fetches all video metadata but only transcripts for first N videos.
        """
        try:
            self._emit('status', {'message': f'Extracting channel ID from URL: {channel_url}'})
            channel_id = self.yt_client.extract_channel_id(channel_url)

            if not channel_id:
                raise ValueError('Could not extract channel ID from URL')

            self._emit('channel_id_extracted', {'channel_id': channel_id})

            # Get channel info
            self._emit('status', {'message': 'Fetching channel information...'})
            channel_info = self.yt_client.get_channel_info(channel_id)

            if not channel_info:
                raise ValueError('Could not fetch channel information')

            self._emit('channel_info', {
                'channel_name': channel_info['channel_name'],
                'description': channel_info['description'][:100] + '...' if len(channel_info['description']) > 100 else channel_info['description']
            })

            # Check if channel exists
            existing_channel = self.db.query(Channel).filter(
                Channel.channel_id == channel_id
            ).first()

            if existing_channel:
                self._emit('status', {'message': f'Channel already exists: {existing_channel.channel_name}'})
                db_channel = existing_channel
            else:
                self._emit('status', {'message': f'Adding new channel: {channel_info["channel_name"]}'})
                db_channel = Channel(
                    channel_id=channel_id,
                    channel_name=channel_info['channel_name'],
                    channel_url=channel_url,
                    description=channel_info['description'],
                    last_checked=datetime.utcnow()
                )
                self.db.add(db_channel)

            self.db.commit()
            self.db.refresh(db_channel)

            # Fetch all videos
            self._emit('status', {'message': 'Fetching all videos from channel...'})
            videos = self.yt_client.get_all_videos(channel_info['uploads_playlist_id'])

            self._emit('videos_found', {'count': len(videos)})

            # Add all video metadata
            new_videos = 0
            for video_data in videos:
                existing_video = self.db.query(Video).filter(
                    Video.video_id == video_data['video_id']
                ).first()

                if not existing_video:
                    db_video = Video(
                        channel_id=db_channel.id,
                        video_id=video_data['video_id'],
                        title=video_data['title'],
                        description=video_data['description'],
                        published_at=datetime.fromisoformat(video_data['published_at'].replace('Z', '+00:00')),
                        thumbnail_url=video_data['thumbnail_url']
                    )
                    self.db.add(db_video)
                    new_videos += 1

            self.db.commit()

            # Fetch transcripts for first N videos only
            videos_to_scrape = videos[:transcript_limit]
            new_transcripts = 0
            stopped_early = False

            for idx, video_data in enumerate(videos_to_scrape, 1):
                video_id = video_data['video_id']

                self._emit('video_progress', {
                    'current': idx,
                    'total': len(videos_to_scrape),
                    'video_id': video_id,
                    'title': video_data['title']
                })

                # Get the video from DB
                db_video = self.db.query(Video).filter(
                    Video.video_id == video_id
                ).first()

                # Check if transcript exists
                existing_transcript = self.db.query(Transcript).filter(
                    Transcript.video_id == db_video.id
                ).first()

                if existing_transcript:
                    self._emit('video_status', {'status': 'has_transcript'})
                    continue

                # Fetch transcript
                self._emit('video_status', {'status': 'fetching_transcript'})

                try:
                    transcript_data, error_data = self.transcript_fetcher.fetch_transcript(video_id)
                except IpBlockedException as e:
                    self._emit('error', {
                        'message': f'IP blocked after processing {idx} videos. Stopping transcript fetching.'
                    })
                    stopped_early = True
                    break

                if transcript_data:
                    db_transcript = Transcript(
                        video_id=db_video.id,
                        text=transcript_data['text'],
                        snippets=transcript_data['snippets'],
                        language_code=transcript_data['language_code'],
                        is_generated=transcript_data['is_generated']
                    )
                    self.db.add(db_transcript)
                    self.db.commit()
                    new_transcripts += 1
                    self._emit('video_status', {
                        'status': 'transcript_saved',
                        'length': len(transcript_data['text'])
                    })
                elif error_data:
                    db_error = TranscriptError(
                        video_id=db_video.id,
                        error_type=error_data['error_type'],
                        error_message=error_data['error_message']
                    )
                    self.db.add(db_error)
                    self.db.commit()
                    self._emit('video_status', {
                        'status': 'error',
                        'error_type': error_data['error_type']
                    })

            # Update channel last_checked
            db_channel.last_checked = datetime.utcnow()
            self.db.commit()

            summary = {
                'channel_id': channel_id,
                'channel_name': channel_info['channel_name'],
                'total_videos': len(videos),
                'new_videos': new_videos,
                'new_transcripts': new_transcripts,
                'transcripts_scraped': len(videos_to_scrape) if not stopped_early else idx,
                'stopped_early': stopped_early
            }

            self._emit('complete', summary)

            return summary

        except Exception as e:
            self._emit('error', {'message': str(e)})
            raise

    def fetch_missing_transcripts(self, channel_id: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch transcripts for videos that don't have them yet (never attempted)"""
        channel = self.db.query(Channel).filter(
            Channel.channel_id == channel_id
        ).first()

        if not channel:
            raise ValueError('Channel not found')

        self._emit('status', {'message': f'Fetching missing transcripts: {channel.channel_name}'})

        # Get videos without transcripts AND without errors (never attempted)
        videos_with_errors = self.db.query(TranscriptError.video_id).distinct()

        videos_without_transcripts = self.db.query(Video).outerjoin(Transcript).filter(
            Video.channel_id == channel.id,
            Transcript.id == None,
            ~Video.id.in_(videos_with_errors)
        ).order_by(Video.published_at.desc())

        if limit:
            videos_without_transcripts = videos_without_transcripts.limit(limit)

        videos_to_fetch = videos_without_transcripts.all()

        self._emit('videos_to_retry', {'count': len(videos_to_fetch)})

        if not videos_to_fetch:
            summary = {
                'channel_name': channel.channel_name,
                'videos_processed': 0,
                'new_transcripts': 0
            }
            self._emit('complete', summary)
            return summary

        success_count = 0
        stopped_early = False

        for idx, video in enumerate(videos_to_fetch, 1):
            self._emit('video_progress', {
                'current': idx,
                'total': len(videos_to_fetch),
                'video_id': video.video_id,
                'title': video.title
            })

            try:
                transcript_data, error_data = self.transcript_fetcher.fetch_transcript(video.video_id)
            except IpBlockedException as e:
                self._emit('error', {
                    'message': f'IP blocked after processing {idx} videos. Stopping transcript fetching.'
                })
                stopped_early = True
                break

            if transcript_data:
                db_transcript = Transcript(
                    video_id=video.id,
                    text=transcript_data['text'],
                    snippets=transcript_data['snippets'],
                    language_code=transcript_data['language_code'],
                    is_generated=transcript_data['is_generated']
                )
                self.db.add(db_transcript)
                self.db.commit()
                success_count += 1
                self._emit('video_status', {
                    'status': 'transcript_saved',
                    'length': len(transcript_data['text'])
                })
            elif error_data:
                db_error = TranscriptError(
                    video_id=video.id,
                    error_type=error_data['error_type'],
                    error_message=error_data['error_message']
                )
                self.db.add(db_error)
                self.db.commit()
                self._emit('video_status', {
                    'status': 'error',
                    'error_type': error_data['error_type']
                })

        summary = {
            'channel_name': channel.channel_name,
            'videos_processed': len(videos_to_fetch) if not stopped_early else idx,
            'new_transcripts': success_count,
            'stopped_early': stopped_early
        }

        self._emit('complete', summary)

        return summary