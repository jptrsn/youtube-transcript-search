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

        Args:
            query: Search query string
            limit: Maximum number of results
            exact_match: If True, only return exact phrase matches
            min_similarity: Minimum similarity score for fuzzy matches (0-1)

        Returns:
            List of search results with video info, match location, and snippets
        """

        # Prepare the search query for PostgreSQL full-text search
        ts_query = self._prepare_tsquery(query, exact_match)

        # Build the search query with ranking
        results = []

        # Search in transcripts (highest priority)
        transcript_results = self._search_transcripts(ts_query, query, limit, min_similarity)
        results.extend(transcript_results)

        # Search in video titles (medium priority)
        title_results = self._search_titles(ts_query, query, limit, min_similarity)
        results.extend(title_results)

        # Search in video descriptions (lowest priority)
        description_results = self._search_descriptions(ts_query, query, limit, min_similarity)
        results.extend(description_results)

        # Remove duplicates (keep highest ranking match per video)
        seen_video_ids = set()
        unique_results = []
        for result in results:
            if result['video_id'] not in seen_video_ids:
                seen_video_ids.add(result['video_id'])
                unique_results.append(result)

        # Sort by rank and limit
        unique_results.sort(key=lambda x: x['rank'], reverse=True)
        return unique_results[:limit]

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
        """Search in video transcripts"""

        # Check for phrase match (case-insensitive containment)
        lower_query = original_query.lower()

        # Full-text search query
        search_results = self.db.query(
            Video,
            Transcript,
            Channel,
            func.ts_rank(Transcript.text_search_vector, func.to_tsquery('english', ts_query)).label('ts_rank'),
            func.similarity(Transcript.text, original_query).label('similarity'),
            # Check if exact phrase exists
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
                rank = 100 + (ts_rank * 10) + (similarity * 5)  # Exact phrases get massive boost
            else:
                rank = (ts_rank * 10) + (similarity * 5)

            # Extract snippet around the match
            snippet = self._extract_snippet(transcript.text, original_query)

            # Find timestamp of the match
            timestamp = self._find_timestamp(transcript.snippets, original_query)

            results.append({
                'video_id': video.video_id,
                'title': video.title,
                'channel_name': channel.channel_name,
                'thumbnail_url': video.thumbnail_url,
                'published_at': video.published_at.isoformat(),
                'match_type': 'transcript',
                'snippet': snippet,
                'timestamp': timestamp,
                'rank': rank
            })

        return results

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