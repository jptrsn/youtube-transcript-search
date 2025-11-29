from sqlalchemy import func, or_, and_, case, literal_column
from sqlalchemy.orm import Session
from backend.models import Video, Transcript, Channel
from typing import List, Dict, Optional
import re

class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query: str,
        limit: int = 20,
        exact_match: bool = False,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """
        Search across video titles, descriptions, and transcripts.
        Returns ALL matches per video, limited by number of videos.

        Args:
            query: Search query string
            limit: Maximum number of VIDEOS to return (not total matches)
            exact_match: If True, only return exact phrase matches
            min_similarity: Minimum similarity score for fuzzy matches (0-1)

        Returns:
            List of search results with video info, match location, and snippets
        """

        # Prepare the search query for PostgreSQL full-text search
        ts_query = self._prepare_tsquery(query, exact_match)

        # Search and get results grouped by video
        transcript_results = self._search_transcripts(ts_query, query, limit, min_similarity)
        title_results = self._search_titles(ts_query, query, limit, min_similarity)
        description_results = self._search_descriptions(ts_query, query, limit, min_similarity)

        # Combine all results
        all_results = transcript_results + title_results + description_results

        # Group by video_id and keep all matches per video
        videos_dict = {}
        for result in all_results:
            video_id = result['video_id']
            if video_id not in videos_dict:
                videos_dict[video_id] = {
                    'video_id': video_id,
                    'title': result['title'],
                    'channel_name': result['channel_name'],
                    'thumbnail_url': result['thumbnail_url'],
                    'published_at': result['published_at'],
                    'max_rank': result['rank'],
                    'matches': []
                }
            else:
                # Update max rank if this match has higher rank
                videos_dict[video_id]['max_rank'] = max(videos_dict[video_id]['max_rank'], result['rank'])

            videos_dict[video_id]['matches'].append({
                'match_type': result['match_type'],
                'snippet': result['snippet'],
                'timestamp': result['timestamp'],
                'rank': result['rank']
            })

        # Convert to list and sort by max rank
        videos_list = list(videos_dict.values())
        videos_list.sort(key=lambda x: x['max_rank'], reverse=True)

        # Limit to top N videos
        top_videos = videos_list[:limit]

        # Flatten back to individual results
        final_results = []
        for video in top_videos:
            for match in video['matches']:
                final_results.append({
                    'video_id': video['video_id'],
                    'title': video['title'],
                    'channel_name': video['channel_name'],
                    'thumbnail_url': video['thumbnail_url'],
                    'published_at': video['published_at'],
                    'match_type': match['match_type'],
                    'snippet': match['snippet'],
                    'timestamp': match['timestamp'],
                    'rank': match['rank']
                })

        return final_results

    def _prepare_tsquery(self, query: str, exact_match: bool) -> str:
      """Convert search query to PostgreSQL tsquery format"""
      # Clean the query - remove punctuation except spaces
      cleaned = re.sub(r"[^\w\s]", "", query)
      words = cleaned.lower().split()

      if not words:
          return query.lower()

      if exact_match:
          # For exact phrase matching, use <-> operator (words must be adjacent)
          return ' <-> '.join(words)
      else:
          # Default: treat multi-word queries as phrases
          if len(words) > 1:
              # Use <-> for phrase matching but allow some flexibility with <N>
              return ' <-> '.join(words)
          else:
              # Single word - just search for that word
              return words[0]

    def _search_transcripts(
        self,
        ts_query: str,
        original_query: str,
        limit: int,
        min_similarity: float
    ) -> List[Dict]:
        """Search in video transcripts - returns ALL matches within each video"""

        lower_query = original_query.lower()

        # Full-text search query
        search_results = self.db.query(
            Video,
            Transcript,
            Channel,
            func.ts_rank(Transcript.text_search_vector, func.to_tsquery('english', ts_query)).label('ts_rank'),
            func.similarity(Transcript.text, original_query).label('similarity'),
            Transcript.text.ilike(f'%{original_query}%').label('has_phrase')
        ).join(
            Transcript, Video.id == Transcript.video_id
        ).join(
            Channel, Video.channel_id == Channel.id
        ).filter(
            or_(
                Transcript.text_search_vector.op('@@')(func.to_tsquery('english', ts_query)),
                func.similarity(Transcript.text, original_query) > min_similarity,
                Transcript.text.ilike(f'%{original_query}%')
            )
        ).limit(limit * 2).all()

        results = []
        for video, transcript, channel, ts_rank, similarity, has_phrase in search_results:
            # Calculate combined rank with HUGE boost for exact phrase matches
            if has_phrase:
                rank = 100 + (ts_rank * 10) + (similarity * 5)
            else:
                rank = (ts_rank * 10) + (similarity * 5)

            # Find ALL occurrences of the query in the transcript
            matches = self._find_all_matches(transcript.text, transcript.snippets, original_query)

            # Create a result for each match
            for match in matches:
                results.append({
                    'video_id': video.video_id,
                    'title': video.title,
                    'channel_name': channel.channel_name,
                    'thumbnail_url': video.thumbnail_url,
                    'published_at': video.published_at.isoformat(),
                    'match_type': 'transcript',
                    'snippet': match['snippet'],
                    'timestamp': match['timestamp'],
                    'rank': rank
                })

        return results

    def _find_all_matches(self, text: str, snippets: List[Dict], query: str, context_chars: int = 150) -> List[Dict]:
        """Find all occurrences of query in text and return snippet + timestamp for each"""
        if not text:
            return []

        lower_text = text.lower()
        lower_query = query.lower()
        matches = []

        # Find all positions where the query appears
        start = 0
        while True:
            pos = lower_text.find(lower_query, start)
            if pos == -1:
                break

            # Extract snippet around this match
            snippet_start = max(0, pos - context_chars)
            snippet_end = min(len(text), pos + len(query) + context_chars)
            snippet = text[snippet_start:snippet_end]

            if snippet_start > 0:
                snippet = "..." + snippet
            if snippet_end < len(text):
                snippet = snippet + "..."

            # Find timestamp for this occurrence
            timestamp = self._find_timestamp_for_position(snippets, pos, text)

            matches.append({
                'snippet': snippet.strip(),
                'timestamp': timestamp
            })

            # Move past this occurrence
            start = pos + len(query)

        return matches if matches else [{'snippet': text[:context_chars * 2] + "...", 'timestamp': None}]

    def _find_timestamp_for_position(self, snippets: List[Dict], char_position: int, full_text: str) -> Optional[float]:
        """Find the timestamp for a character position in the full transcript text"""
        if not snippets:
            return None

        # Build a map of character positions to timestamps
        current_pos = 0
        for snippet in snippets:
            snippet_text = snippet['text']
            snippet_len = len(snippet_text)

            # Check if our position falls within this snippet
            if current_pos <= char_position < current_pos + snippet_len:
                return snippet['start']

            current_pos += snippet_len + 1  # +1 for the space that joins snippets

        # If not found, return the first snippet's timestamp
        return snippets[0]['start'] if snippets else None

    def _search_titles(
        self,
        ts_query: str,
        original_query: str,
        limit: int,
        min_similarity: float
    ) -> List[Dict]:
        """Search in video titles"""

        search_results = self.db.query(
            Video,
            Channel,
            func.ts_rank(Video.title_search_vector, func.to_tsquery('english', ts_query)).label('ts_rank'),
            func.similarity(Video.title, original_query).label('similarity')
        ).join(
            Channel, Video.channel_id == Channel.id
        ).filter(
            or_(
                Video.title_search_vector.op('@@')(func.to_tsquery('english', ts_query)),
                func.similarity(Video.title, original_query) > min_similarity
            )
        ).limit(limit * 2).all()

        results = []
        for video, channel, ts_rank, similarity in search_results:
            rank = (ts_rank * 5) + (similarity * 3)  # Title results get 5x weight

            results.append({
                'video_id': video.video_id,
                'title': video.title,
                'channel_name': channel.channel_name,
                'thumbnail_url': video.thumbnail_url,
                'published_at': video.published_at.isoformat(),
                'match_type': 'title',
                'snippet': video.title,
                'timestamp': None,
                'rank': rank
            })

        return results

    def _search_descriptions(
        self,
        ts_query: str,
        original_query: str,
        limit: int,
        min_similarity: float
    ) -> List[Dict]:
        """Search in video descriptions"""

        search_results = self.db.query(
            Video,
            Channel,
            func.ts_rank(Video.description_search_vector, func.to_tsquery('english', ts_query)).label('ts_rank'),
            func.similarity(Video.description, original_query).label('similarity')
        ).join(
            Channel, Video.channel_id == Channel.id
        ).filter(
            and_(
                Video.description.isnot(None),
                or_(
                    Video.description_search_vector.op('@@')(func.to_tsquery('english', ts_query)),
                    func.similarity(Video.description, original_query) > min_similarity
                )
            )
        ).limit(limit * 2).all()

        results = []
        for video, channel, ts_rank, similarity in search_results:
            rank = (ts_rank * 2) + (similarity * 1)  # Description results get 2x weight

            snippet = self._extract_snippet(video.description or '', original_query)

            results.append({
                'video_id': video.video_id,
                'title': video.title,
                'channel_name': channel.channel_name,
                'thumbnail_url': video.thumbnail_url,
                'published_at': video.published_at.isoformat(),
                'match_type': 'description',
                'snippet': snippet,
                'timestamp': None,
                'rank': rank
            })

        return results

    def _extract_snippet(self, text: str, query: str, context_chars: int = 150) -> str:
        """Extract a snippet of text around the search query match"""
        if not text:
            return ""

        # Find the query in the text (case-insensitive)
        lower_text = text.lower()
        lower_query = query.lower()

        # Try to find exact phrase first
        pos = lower_text.find(lower_query)

        # If exact phrase not found, find first word of query
        if pos == -1:
            words = lower_query.split()
            for word in words:
                pos = lower_text.find(word)
                if pos != -1:
                    break

        # If still not found, return beginning of text
        if pos == -1:
            return text[:context_chars * 2] + "..."

        # Calculate snippet boundaries
        start = max(0, pos - context_chars)
        end = min(len(text), pos + len(query) + context_chars)

        # Extract snippet
        snippet = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet.strip()

    def _find_timestamp(self, snippets: List[Dict], query: str) -> Optional[float]:
        """Find the timestamp where the query appears in the transcript"""
        if not snippets:
            return None

        lower_query = query.lower()

        for snippet in snippets:
            if lower_query in snippet['text'].lower():
                return snippet['start']

        return None