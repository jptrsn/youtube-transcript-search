export interface TranscriptSegment {
  text: string;
  start: number;
  duration: number;
}

/**
 * Search transcript segments for a query string
 * @param segments - Array of transcript segments
 * @param query - Search query (case-insensitive)
 * @returns Array of matching segments
 */
export function searchTranscript(
  segments: TranscriptSegment[],
  query: string
): TranscriptSegment[] {
  const normalizedQuery = query.trim().toLowerCase();

  if (!normalizedQuery) {
    return [];
  }

  return segments.filter(segment =>
    segment.text.toLowerCase().includes(normalizedQuery)
  );
}