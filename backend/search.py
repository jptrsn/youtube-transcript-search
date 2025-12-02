from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict
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
        Optimized search that returns match counts and best snippet per video.

        Returns:
            List of videos with: {
                video_id, title, channel_name, thumbnail_url, published_at,
                transcript_matches: int,
                title_matches: int,
                description_matches: int,
                best_snippet: str,
                best_timestamp: float,
                rank: float
            }
        """
        ts_query = self._prepare_tsquery(query, exact_match)

        # Single optimized query using UNION ALL and aggregation
        sql = text("""
            WITH search_results AS (
                -- Transcript matches
                SELECT
                    v.id as video_id,
                    v.video_id as video_yt_id,
                    v.title,
                    v.thumbnail_url,
                    v.published_at,
                    c.channel_name,
                    'transcript' as match_type,
                    ts_rank(t.text_search_vector, to_tsquery('english', :ts_query)) * 10
                        + similarity(t.text, :original_query) * 5
                        + CASE WHEN t.text ILIKE :like_query THEN 100 ELSE 0 END as rank,
                    ts_headline('english', t.text, to_tsquery('english', :ts_query),
                        'StartSel=<<, StopSel=>>, MaxWords=50, MinWords=25') as snippet,
                    (
                        SELECT (s->>'start')::float
                        FROM jsonb_array_elements(t.snippets) as s
                        WHERE lower(s->>'text') LIKE :like_query_lower
                        LIMIT 1
                    ) as timestamp
                FROM videos v
                JOIN transcripts t ON v.id = t.video_id
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    t.text_search_vector @@ to_tsquery('english', :ts_query)
                    OR similarity(t.text, :original_query) > :min_similarity
                    OR t.text ILIKE :like_query

                UNION ALL

                -- Title matches
                SELECT
                    v.id,
                    v.video_id,
                    v.title,
                    v.thumbnail_url,
                    v.published_at,
                    c.channel_name,
                    'title',
                    ts_rank(v.title_search_vector, to_tsquery('english', :ts_query)) * 5
                        + similarity(v.title, :original_query) * 3 as rank,
                    v.title as snippet,
                    NULL as timestamp
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    v.title_search_vector @@ to_tsquery('english', :ts_query)
                    OR similarity(v.title, :original_query) > :min_similarity

                UNION ALL

                -- Description matches
                SELECT
                    v.id,
                    v.video_id,
                    v.title,
                    v.thumbnail_url,
                    v.published_at,
                    c.channel_name,
                    'description',
                    ts_rank(v.description_search_vector, to_tsquery('english', :ts_query)) * 2
                        + similarity(v.description, :original_query) * 1 as rank,
                    ts_headline('english', v.description, to_tsquery('english', :ts_query),
                        'StartSel=<<, StopSel=>>, MaxWords=30, MinWords=15') as snippet,
                    NULL as timestamp
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    v.description IS NOT NULL
                    AND (
                        v.description_search_vector @@ to_tsquery('english', :ts_query)
                        OR similarity(v.description, :original_query) > :min_similarity
                    )
            )
            SELECT
                video_yt_id,
                title,
                channel_name,
                thumbnail_url,
                published_at,
                COUNT(*) FILTER (WHERE match_type = 'transcript') as transcript_matches,
                COUNT(*) FILTER (WHERE match_type = 'title') as title_matches,
                COUNT(*) FILTER (WHERE match_type = 'description') as description_matches,
                MAX(rank) as max_rank,
                (
                    SELECT snippet
                    FROM search_results sr2
                    WHERE sr2.video_id = search_results.video_id
                        AND sr2.match_type = 'transcript'
                    ORDER BY sr2.rank DESC
                    LIMIT 1
                ) as best_snippet,
                (
                    SELECT timestamp
                    FROM search_results sr2
                    WHERE sr2.video_id = search_results.video_id
                        AND sr2.match_type = 'transcript'
                    ORDER BY sr2.rank DESC
                    LIMIT 1
                ) as best_timestamp
            FROM search_results
            GROUP BY video_id, video_yt_id, title, channel_name, thumbnail_url, published_at
            ORDER BY max_rank DESC
            LIMIT :limit
        """)

        results = self.db.execute(sql, {
            'ts_query': ts_query,
            'original_query': query,
            'like_query': f'%{query}%',
            'like_query_lower': f'%{query.lower()}%',
            'min_similarity': min_similarity,
            'limit': limit
        }).fetchall()

        return [
            {
                'video_id': row[0],
                'title': row[1],
                'channel_name': row[2],
                'thumbnail_url': row[3],
                'published_at': row[4].isoformat() if row[4] else None,
                'transcript_matches': row[5] or 0,
                'title_matches': row[6] or 0,
                'description_matches': row[7] or 0,
                'rank': float(row[8]) if row[8] else 0,
                'best_snippet': row[9],
                'best_timestamp': float(row[10]) if row[10] else None
            }
            for row in results
        ]

    def _prepare_tsquery(self, query: str, exact_match: bool) -> str:
        """Convert search query to PostgreSQL tsquery format"""
        cleaned = re.sub(r"[^\w\s]", "", query)
        words = cleaned.lower().split()

        if not words:
            return query.lower()

        if exact_match:
            return ' <-> '.join(words)
        else:
            if len(words) > 1:
                return ' <-> '.join(words)
            else:
                return words[0]

    def search_channel(
        self,
        channel_id: str,
        query: str,
        limit: int = 20,
        offset: int = 0,
        exact_match: bool = False,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """Optimized search within a specific channel with pagination."""
        ts_query = self._prepare_tsquery(query, exact_match)

        sql = text("""
            WITH search_results AS (
                -- Transcript matches
                SELECT
                    v.id as video_id,
                    v.video_id as video_yt_id,
                    v.title,
                    v.thumbnail_url,
                    v.published_at,
                    c.channel_name,
                    'transcript' as match_type,
                    ts_rank(t.text_search_vector, to_tsquery('english', :ts_query)) * 10
                        + CASE WHEN t.text ILIKE :like_query THEN 100 ELSE 0 END as rank
                FROM videos v
                JOIN transcripts t ON v.id = t.video_id
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    c.channel_id = :channel_id
                    AND (
                        t.text_search_vector @@ to_tsquery('english', :ts_query)
                        OR t.text ILIKE :like_query
                    )

                UNION ALL

                -- Title matches
                SELECT
                    v.id,
                    v.video_id,
                    v.title,
                    v.thumbnail_url,
                    v.published_at,
                    c.channel_name,
                    'title',
                    ts_rank(v.title_search_vector, to_tsquery('english', :ts_query)) * 5 as rank
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    c.channel_id = :channel_id
                    AND v.title_search_vector @@ to_tsquery('english', :ts_query)

                UNION ALL

                -- Description matches
                SELECT
                    v.id,
                    v.video_id,
                    v.title,
                    v.thumbnail_url,
                    v.published_at,
                    c.channel_name,
                    'description',
                    ts_rank(v.description_search_vector, to_tsquery('english', :ts_query)) * 2 as rank
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    c.channel_id = :channel_id
                    AND v.description IS NOT NULL
                    AND v.description_search_vector @@ to_tsquery('english', :ts_query)
            )
            SELECT
                video_yt_id,
                title,
                channel_name,
                thumbnail_url,
                published_at,
                COUNT(*) FILTER (WHERE match_type = 'transcript') as transcript_matches,
                COUNT(*) FILTER (WHERE match_type = 'title') as title_matches,
                COUNT(*) FILTER (WHERE match_type = 'description') as description_matches,
                MAX(rank) as max_rank
            FROM search_results
            GROUP BY video_id, video_yt_id, title, channel_name, thumbnail_url, published_at
            ORDER BY max_rank DESC
            LIMIT :limit
            OFFSET :offset
        """)

        results = self.db.execute(sql, {
            'channel_id': channel_id,
            'ts_query': ts_query,
            'like_query': f'%{query}%',
            'limit': limit,
            'offset': offset
        }).fetchall()

        return [
            {
                'video_id': row[0],
                'title': row[1],
                'channel_name': row[2],
                'thumbnail_url': row[3],
                'published_at': row[4].isoformat() if row[4] else None,
                'transcript_matches': row[5] or 0,
                'title_matches': row[6] or 0,
                'description_matches': row[7] or 0,
                'rank': float(row[8]) if row[8] else 0
            }
            for row in results
        ]

    def get_batch_snippets(self, video_ids: List[str], query: str) -> Dict[str, Dict]:
        """
        Get best snippets for multiple videos efficiently.
        Returns dict keyed by video_id.
        """
        if not video_ids:
            return {}

        ts_query = self._prepare_tsquery(query, False)

        sql = text("""
            SELECT
                v.video_id,
                REPLACE(REPLACE(
                    ts_headline('english', t.text, to_tsquery('english', :ts_query),
                        'StartSel=<<, StopSel=>>, MaxWords=50, MinWords=25'),
                    '<<', '<mark>'),
                    '>>', '</mark>') as snippet,
                (
                    SELECT (s->>'start')::float
                    FROM jsonb_array_elements(t.snippets) as s
                    WHERE lower(s->>'text') LIKE :like_query_lower
                    LIMIT 1
                ) as timestamp
            FROM transcripts t
            JOIN videos v ON t.video_id = v.id
            WHERE
                v.video_id = ANY(:video_ids)
                AND (
                    t.text_search_vector @@ to_tsquery('english', :ts_query)
                    OR t.text ILIKE :like_query
                )
        """)

        results = self.db.execute(sql, {
            'video_ids': video_ids,
            'ts_query': ts_query,
            'like_query': f'%{query}%',
            'like_query_lower': f'%{query.lower()}%'
        }).fetchall()

        # Build dict keyed by video_id
        snippets = {}
        for row in results:
            snippets[row[0]] = {
                'snippet': row[1],
                'timestamp': float(row[2]) if row[2] else None
            }

        return snippets