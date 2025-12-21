import { API_URL } from '../config';

interface TranscriptSegment {
  text: string;
  start: number;
  duration: number;
}

interface VideoInfo {
  videoId: string;
  channelId: string;
  title: string;
  description: string;
  publishedAt: string;
  thumbnailUrl: string;
}

// Extract video ID from URL
function getVideoId(): string | null {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('v');
}

// Extract channel ID from page data
function getChannelId(): string | null {
  try {
    const scripts = document.querySelectorAll('script');
    for (const script of scripts) {
      const content = script.textContent || '';
      if (content.includes('ytInitialData')) {
        const match = content.match(/"channelId":"([^"]+)"/);
        if (match) return match[1];
      }
    }
  } catch (e) {
    console.error('Error extracting channel ID:', e);
  }
  return null;
}

// Extract video metadata
function getVideoInfo(videoId: string, channelId: string): VideoInfo | null {
  try {
    const scripts = document.querySelectorAll('script');
    for (const script of scripts) {
      const content = script.textContent || '';
      if (content.includes('ytInitialPlayerResponse')) {
        const match = content.match(/ytInitialPlayerResponse\s*=\s*({.+?});/);
        if (match) {
          const playerResponse = JSON.parse(match[1]);
          const details = playerResponse.videoDetails;

          return {
            videoId,
            channelId,
            title: details.title,
            description: details.shortDescription || '',
            publishedAt: new Date().toISOString(),
            thumbnailUrl: details.thumbnail?.thumbnails?.[0]?.url || ''
          };
        }
      }
    }
  } catch (e) {
    console.error('Error extracting video info:', e);
  }
  return null;
}

// Extract InnerTube API key from page scripts
function extractInnertubeApiKey(): string | null {
  try {
    const scripts = document.querySelectorAll('script');
    for (const script of scripts) {
      const content = script.textContent || '';
      const match = content.match(/"INNERTUBE_API_KEY":\s*"([a-zA-Z0-9_-]+)"/);
      if (match) {
        console.log('Found InnerTube API key');
        return match[1];
      }
    }
    console.log('No InnerTube API key found in page scripts');
    return null;
  } catch (e) {
    console.error('Error extracting API key:', e);
    return null;
  }
}

// Fetch captions JSON from YouTube's InnerTube API
async function fetchCaptionsJson(videoId: string, apiKey: string): Promise<any> {
  try {
    const url = `https://www.youtube.com/youtubei/v1/player?key=${apiKey}`;
    const requestBody = {
      context: {
        client: {
          clientName: 'WEB',
          clientVersion: '2.20241212.01.00'
        }
      },
      videoId: videoId,
    };

    console.log('Fetching captions from InnerTube API...');

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    console.log('InnerTube API response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('InnerTube API request failed:', response.status);
      console.error('Error response:', errorText);
      return null;
    }

    const data = await response.json();

    // Check if captions are available
    const captions = data?.captions?.playerCaptionsTracklistRenderer;
    if (!captions || !captions.captionTracks) {
      console.log('No captions available for video');
      return null;
    }

    console.log('Found caption tracks:', captions.captionTracks.length);
    return captions;
  } catch (e) {
    console.error('Error fetching captions JSON:', e);
    return null;
  }
}

// Find English transcript URL from captions JSON
function findEnglishTranscriptUrl(captionsJson: any): string | null {
  try {
    const captionTracks = captionsJson.captionTracks;

    // Look for English transcripts (manual first, then auto-generated)
    const englishCodes = ['en', 'en-US', 'en-GB'];

    // Try to find manually created English transcript first
    for (const code of englishCodes) {
      const manual = captionTracks.find(
        (track: any) => track.languageCode === code && track.kind !== 'asr'
      );
      if (manual) {
        console.log('Found manual English transcript');
        return manual.baseUrl;
      }
    }

    // Fall back to auto-generated English transcript
    for (const code of englishCodes) {
      const auto = captionTracks.find(
        (track: any) => track.languageCode === code && track.kind === 'asr'
      );
      if (auto) {
        console.log('Found auto-generated English transcript');
        return auto.baseUrl;
      }
    }

    console.log('No English transcript found');
    return null;
  } catch (e) {
    console.error('Error finding English transcript URL:', e);
    return null;
  }
}

// Fetch and parse transcript XML
async function fetchAndParseTranscript(url: string): Promise<TranscriptSegment[] | null> {
  try {
    const response = await fetch(url);

    if (!response.ok) {
      console.error('Failed to fetch transcript XML:', response.status);
      return null;
    }

    const xmlText = await response.text();

    // Parse XML using DOMParser
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, 'text/xml');

    // Check for parsing errors
    const parseError = xmlDoc.querySelector('parsererror');
    if (parseError) {
      console.error('XML parsing error:', parseError.textContent);
      return null;
    }

    // Extract transcript segments
    const textElements = xmlDoc.querySelectorAll('text');
    const segments: TranscriptSegment[] = [];

    textElements.forEach(element => {
      const text = element.textContent || '';
      const start = parseFloat(element.getAttribute('start') || '0');
      const duration = parseFloat(element.getAttribute('dur') || '0');

      if (text) {
        segments.push({ text, start, duration });
      }
    });

    console.log(`Parsed ${segments.length} transcript segments`);
    return segments.length > 0 ? segments : null;
  } catch (e) {
    console.error('Error fetching/parsing transcript:', e);
    return null;
  }
}

// Main function to fetch transcript silently via API
async function fetchTranscriptSilently(videoId: string): Promise<TranscriptSegment[] | null> {
  try {
    console.log('Attempting to fetch transcript silently via API...');

    // Step 1: Extract API key from page
    const apiKey = extractInnertubeApiKey();
    if (!apiKey) {
      console.log('Could not extract API key, falling back to UI method');
      return null;
    }

    // Step 2: Fetch captions JSON from InnerTube API
    const captionsJson = await fetchCaptionsJson(videoId, apiKey);
    if (!captionsJson) {
      console.log('Could not fetch captions JSON, falling back to UI method');
      return null;
    }

    // Step 3: Find English transcript URL
    const transcriptUrl = findEnglishTranscriptUrl(captionsJson);
    if (!transcriptUrl) {
      console.log('No English transcript available, falling back to UI method');
      return null;
    }

    // Step 4: Fetch and parse transcript XML
    const transcript = await fetchAndParseTranscript(transcriptUrl);
    if (!transcript) {
      console.log('Could not parse transcript, falling back to UI method');
      return null;
    }

    console.log('Successfully fetched transcript silently!');
    return transcript;
  } catch (e) {
    console.error('Silent transcript fetch failed:', e);
    return null;
  }
}

// Fetch transcript by opening UI panel and scraping DOM (fallback method)
async function fetchTranscriptFromUI(): Promise<TranscriptSegment[] | null> {
  console.log('Attempting to fetch transcript via UI method...');

  // Open transcript panel
  const panelOpened = await openTranscriptPanel();
  if (!panelOpened) {
    console.log('Could not open transcript panel - video may not have transcript');
    return null;
  }

  // Extract transcript from panel
  const transcript = await extractTranscriptFromPanel();
  if (!transcript || transcript.length === 0) {
    console.log('Could not extract transcript from panel');
    return null;
  }

  console.log('Successfully fetched transcript via UI method');
  return transcript;
}

// Click the "Show transcript" button and wait for panel to load
async function openTranscriptPanel(): Promise<boolean> {
  return new Promise((resolve) => {
    // Look for the "Show transcript" button
    const buttons = document.querySelectorAll('button');

    for (const button of buttons) {
      const text = button.textContent?.toLowerCase() || '';
      if (text.includes('show transcript') || text.includes('transcript')) {
        console.log('Found transcript button, clicking...');
        button.click();

        // Wait for panel to appear
        setTimeout(() => resolve(true), 2000);
        return;
      }
    }

    console.log('Transcript button not found');
    resolve(false);
  });
}

// Extract transcript from the transcript panel DOM
async function extractTranscriptFromPanel(): Promise<TranscriptSegment[] | null> {
  try {
    // Wait a bit for the panel to fully render
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Find transcript segments in the panel
    const segments: TranscriptSegment[] = [];

    // YouTube transcript items have specific selectors
    const transcriptItems = document.querySelectorAll('ytd-transcript-segment-renderer');

    console.log('Found transcript items:', transcriptItems.length);

    if (transcriptItems.length === 0) {
      console.log('No transcript items found in panel');
      return null;
    }

    transcriptItems.forEach(item => {
      const timeElement = item.querySelector('.segment-timestamp');
      const textElement = item.querySelector('.segment-text');

      if (timeElement && textElement) {
        const timeText = timeElement.textContent?.trim() || '0:00';
        const text = textElement.textContent?.trim() || '';

        // Convert timestamp to seconds
        const parts = timeText.split(':').map(Number);
        let seconds = 0;
        if (parts.length === 2) {
          seconds = parts[0] * 60 + parts[1];
        } else if (parts.length === 3) {
          seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
        }

        segments.push({
          text,
          start: seconds,
          duration: 0 // YouTube doesn't provide duration in the panel
        });
      }
    });

    return segments.length > 0 ? segments : null;
  } catch (e) {
    console.error('Error extracting transcript from panel:', e);
    return null;
  }
}

// Check if video already exists and has transcript
async function checkVideoStatus(videoId: string): Promise<{exists: boolean, hasTranscript: boolean}> {
  try {
    const response = await fetch(`${API_URL}/api/videos/${videoId}/exists`);
    const data = await response.json();
    return {
      exists: data.exists === true,
      hasTranscript: data.has_transcript === true
    };
  } catch (e) {
    console.error('Error checking video status:', e);
    return { exists: false, hasTranscript: false };
  }
}

// Submit video and transcript to API
async function submitTranscript(videoInfo: VideoInfo, transcript: TranscriptSegment[]): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/api/videos/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        video: videoInfo,
        transcript: transcript
      })
    });

    return response.ok;
  } catch (e) {
    console.error('Error submitting transcript:', e);
    return false;
  }
}

// Update extension icon to show success
function updateIcon(success: boolean) {
  chrome.runtime.sendMessage({
    type: 'UPDATE_ICON',
    success
  });
}

// Main execution
async function processVideo() {
  const videoId = getVideoId();
  if (!videoId) return;

  console.log('Processing video:', videoId);

  // Check if video already exists and has transcript
  const status = await checkVideoStatus(videoId);
  if (status.exists && status.hasTranscript) {
    console.log('Video already has transcript in database');
    return;
  }

  if (status.exists && !status.hasTranscript) {
    console.log('Video exists but missing transcript, fetching...');
  } else {
    console.log('New video, fetching transcript...');
  }

  const channelId = getChannelId();
  if (!channelId) {
    console.log('Could not extract channel ID');
    return;
  }

  const videoInfo = getVideoInfo(videoId, channelId);
  if (!videoInfo) {
    console.log('Could not extract video info');
    return;
  }

  // Try silent method first
  let transcript = await fetchTranscriptSilently(videoId);

  // Fallback to UI method if silent fails
  if (!transcript) {
    console.log('Silent method failed, trying UI method...');
    transcript = await fetchTranscriptFromUI();
  }

  if (!transcript || transcript.length === 0) {
    console.log('Could not fetch transcript via any method');
    return;
  }

  console.log('Submitting transcript...', { videoId, segments: transcript.length });
  const success = await submitTranscript(videoInfo, transcript);

  if (success) {
    console.log('Transcript submitted successfully');
    updateIcon(true);

    // Reset icon after 3 seconds
    setTimeout(() => updateIcon(false), 3000);
  }
}

// Watch for URL changes (YouTube SPA navigation)
let lastVideoId: string | null = null;
let isProcessing = false;
let hasInitialRun = false;

async function checkForNewVideo() {
  const currentVideoId = getVideoId();

  if (currentVideoId && currentVideoId !== lastVideoId && !isProcessing) {
    console.log('New video detected:', currentVideoId);
    lastVideoId = currentVideoId;
    isProcessing = true;

    await processVideo();

    isProcessing = false;
  }
}

// Listen to YouTube's SPA navigation events (only for subsequent navigations)
window.addEventListener('yt-navigate-finish', () => {
  // Only handle navigation events after initial run
  if (hasInitialRun) {
    console.log('YouTube navigation detected');
    setTimeout(checkForNewVideo, 1000);
  }
});

// Initial run (only once on page load)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
      lastVideoId = getVideoId();
      processVideo();
      hasInitialRun = true;
    }, 3000);
  });
} else {
  setTimeout(() => {
    lastVideoId = getVideoId();
    processVideo();
    hasInitialRun = true;
  }, 3000);
}

export {};