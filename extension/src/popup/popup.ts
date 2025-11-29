import { API_URL } from '../config';

const searchInput = document.getElementById('searchInput') as HTMLInputElement;
const searchButton = document.getElementById('searchButton') as HTMLButtonElement;
const message = document.getElementById('message') as HTMLDivElement;

// Get current tab's channel ID
async function getCurrentChannelId(): Promise<string | null> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  console.log('Current tab:', tab);

  if (!tab.url) {
    console.log('No tab URL');
    return null;
  }

  console.log('Tab URL:', tab.url);

  // Extract channel ID from URL patterns
  const patterns = [
    /youtube\.com\/channel\/([^/?]+)/,
    /youtube\.com\/@([^/?]+)/,
    /youtube\.com\/watch\?v=([^&]+)/  // We'll need to resolve this
  ];

  for (const pattern of patterns) {
    const match = tab.url.match(pattern);
    if (match) {
      const identifier = match[1];

      // If it's a handle (@username), resolve it
      if (tab.url.includes('/@')) {
        return await resolveHandle(identifier);
      }

      // If it's a watch URL, get channel from page
      if (tab.url.includes('/watch')) {
        return await getChannelFromTab(tab.id!);
      }

      return identifier;
    }
  }

  return null;
}

// Resolve handle to channel ID
async function resolveHandle(handle: string): Promise<string | null> {
  try {
    const response = await fetch(`${API_URL}/api/channels/resolve-handle/${handle}`);
    if (!response.ok) return null;

    const data = await response.json();
    return data.channel_id;
  } catch (e) {
    console.error('Error resolving handle:', e);
    return null;
  }
}

// Get channel ID from the current tab's page
async function getChannelFromTab(tabId: number): Promise<string | null> {
  try {
    console.log('Attempting to execute script in tab', tabId);

    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => {
        // Extract channel ID from page
        const scripts = document.querySelectorAll('script');
        console.log('Found scripts:', scripts.length);

        for (const script of scripts) {
          const content = script.textContent || '';
          if (content.includes('ytInitialData')) {
            const match = content.match(/"channelId":"([^"]+)"/);
            if (match) {
              console.log('Found channel ID:', match[1]);
              return match[1];
            }
          }
        }
        console.log('No channel ID found in scripts');
        return null;
      }
    });

    console.log('Script execution results:', results);
    return results[0]?.result || null;
  } catch (e) {
    console.error('Error getting channel from tab:', e);
    showMessage(`Error: ${e}`, true);
    return null;
  }
}

// Perform search
async function performSearch() {
  const query = searchInput.value.trim();

  if (!query) {
    showMessage('Please enter a search query', true);
    return;
  }

  showMessage('Getting channel info...');

  // Get channel ID fresh each time
  const channelId = await getCurrentChannelId();

  if (!channelId) {
    showMessage('Please navigate to a YouTube channel or video first', true);
    return;
  }

  // Open search results in new tab
  const searchUrl = `${API_URL}/channel/${channelId}?q=${encodeURIComponent(query)}`;
  chrome.tabs.create({ url: searchUrl });

  // Close popup
  window.close();
}

// Show message to user
function showMessage(text: string, isError: boolean = false) {
  message.textContent = text;
  message.className = isError ? 'message error' : 'message';
}

// Event listeners
searchButton.addEventListener('click', performSearch);
searchInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    performSearch();
  }
});

export {};