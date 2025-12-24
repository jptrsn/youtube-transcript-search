import { TranscriptSegment, searchTranscript } from '../utils/search';

export interface SearchResult extends TranscriptSegment {
  // Just using TranscriptSegment directly
}

/**
 * Search transcript via service worker
 * @param videoId - The YouTube video ID
 * @param query - Search query string
 * @returns Promise resolving to array of matching segments
 */
export async function searchVideoTranscript(
  videoId: string,
  query: string
): Promise<TranscriptSegment[]> {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      {
        type: 'SEARCH_TRANSCRIPT',
        videoId,
        query
      },
      (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }

        if (!response.success) {
          reject(new Error(response.error || 'Search failed'));
          return;
        }

        resolve(response.results || []);
      }
    );
  });
}

/**
 * Seek video to timestamp by sending message to content script
 * @param tabId - The tab ID containing the YouTube video
 * @param timestamp - Timestamp in seconds
 */
export async function seekToTimestamp(
  tabId: number,
  timestamp: number
): Promise<void> {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(
      tabId,
      {
        type: 'SEEK_VIDEO',
        timestamp
      },
      (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }

        if (!response.success) {
          reject(new Error(response.error || 'Failed to seek video'));
          return;
        }

        resolve();
      }
    );
  });
}

/**
 * Format timestamp from seconds to MM:SS or HH:MM:SS
 */
export function formatTimestamp(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}