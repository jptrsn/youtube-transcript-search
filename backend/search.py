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
    ) -> tuple[List[Dict], int]:
        """Optimized search within a specific channel with pagination. Returns (results, total_count)."""
        ts_query = self._prepare_tsquery(query, exact_match)

        # First, get total count
        count_sql = text("""
            WITH search_results AS (
                SELECT DISTINCT v.id as video_id
                FROM videos v
                JOIN transcripts t ON v.id = t.video_id
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    c.channel_id = :channel_id
                    AND (
                        t.text_search_vector @@ to_tsquery('english', :ts_query)
                        OR t.text ILIKE :like_query
                    )

                UNION

                SELECT DISTINCT v.id
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    c.channel_id = :channel_id
                    AND v.title_search_vector @@ to_tsquery('english', :ts_query)

                UNION

                SELECT DISTINCT v.id
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    c.channel_id = :channel_id
                    AND v.description IS NOT NULL
                    AND v.description_search_vector @@ to_tsquery('english', :ts_query)
            )
            SELECT COUNT(DISTINCT video_id) FROM search_results
        """)

        total_count = self.db.execute(count_sql, {
            'channel_id': channel_id,
            'ts_query': ts_query,
            'like_query': f'%{query}%'
        }).scalar()

        # Then get the paginated results
        sql = text("""
            WITH search_results AS (
                SELECT
                    v.id as video_id,
                    v.video_id as video_yt_id,
                    v.title,
                    v.thumbnail_url,
                    v.published_at,
                    c.channel_name,
                    'transcript' as match_type,
                    ts_rank(t.text_search_vector, to_tsquery('english', :ts_query)) * 10
                        + CASE WHEN t.text ILIKE :like_query THEN 100 ELSE 0 END as rank,
                    (LENGTH(LOWER(t.text)) - LENGTH(REPLACE(LOWER(t.text), LOWER(:query), ''))) / LENGTH(:query) as transcript_match_count
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

                SELECT
                    v.id,
                    v.video_id,
                    v.title,
                    v.thumbnail_url,
                    v.published_at,
                    c.channel_name,
                    'title',
                    ts_rank(v.title_search_vector, to_tsquery('english', :ts_query)) * 5 as rank,
                    0 as transcript_match_count
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                WHERE
                    c.channel_id = :channel_id
                    AND v.title_search_vector @@ to_tsquery('english', :ts_query)

                UNION ALL

                SELECT
                    v.id,
                    v.video_id,
                    v.title,
                    v.thumbnail_url,
                    v.published_at,
                    c.channel_name,
                    'description',
                    ts_rank(v.description_search_vector, to_tsquery('english', :ts_query)) * 2 as rank,
                    0 as transcript_match_count
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
                MAX(transcript_match_count)::int as transcript_matches,
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
            'query': query,  # Add the raw query for counting
            'like_query': f'%{query}%',
            'limit': limit,
            'offset': offset
        }).fetchall()

        result_list = [
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

        return result_list, total_count

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
                CASE
                    WHEN position(lower(:query) in lower(t.text)) > 0 THEN
                        CASE WHEN position(lower(:query) in lower(t.text)) > 75 THEN '...' ELSE '' END ||
                        SUBSTRING(
                            t.text,
                            GREATEST(1, position(lower(:query) in lower(t.text)) - 75),
                            150 + LENGTH(:query)
                        ) ||
                        CASE WHEN position(lower(:query) in lower(t.text)) + LENGTH(:query) + 75 < LENGTH(t.text) THEN '...' ELSE '' END
                    ELSE
                        SUBSTRING(t.text, 1, 200) || '...'
                END as snippet,
                (
                    SELECT (elem->>'start')::float
                    FROM jsonb_array_elements(t.snippets) elem
                    WHERE position(lower(:query) in lower(elem->>'text')) > 0
                    ORDER BY (elem->>'start')::float
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
            'query': query
        }).fetchall()

        # Build dict with manual highlighting
        import re
        snippets = {}
        for row in results:
            raw_snippet = row[1]
            # Add <mark> tags around the query in the snippet (case-insensitive)
            if raw_snippet and query:
                highlighted = re.sub(
                    f'({re.escape(query)})',
                    r'<mark>\1</mark>',
                    raw_snippet,
                    flags=re.IGNORECASE
                )
            else:
                highlighted = raw_snippet

            snippets[row[0]] = {
                'snippet': highlighted,
                'timestamp': float(row[2]) if row[2] else None
            }

        return snippets

    def get_all_video_matches(self, video_id: str, query: str) -> List[Dict]:
        """
        Get all matches of a query in a video's transcript, chronologically ordered.
        Returns list of {timestamp, snippet, text}
        """
        sql = text("""
            WITH snippet_data AS (
                SELECT
                    (elem->>'start')::float as start_time,
                    elem->>'text' as snippet_text,
                    row_number() OVER () as rn
                FROM transcripts t
                JOIN videos v ON t.video_id = v.id
                CROSS JOIN jsonb_array_elements(t.snippets) elem
                WHERE v.video_id = :video_id
            )
            SELECT
                start_time as timestamp,
                snippet_text as text
            FROM snippet_data
            WHERE lower(snippet_text) LIKE :like_query
            ORDER BY start_time
        """)

        results = self.db.execute(sql, {
            'video_id': video_id,
            'like_query': f'%{query.lower()}%'
        }).fetchall()

        matches = []
        import re

        for row in results:
            timestamp = float(row[0])
            snippet_text = row[1]

            # Highlight the match
            highlighted = re.sub(
                f'({re.escape(query)})',
                r'<mark>\1</mark>',
                snippet_text,
                flags=re.IGNORECASE
            )

            matches.append({
                'timestamp': timestamp,
                'text': highlighted
            })

        return matches