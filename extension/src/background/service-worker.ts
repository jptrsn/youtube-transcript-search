// Background service worker - handles icon updates

// We'll load icons as ImageData instead of using paths
let defaultIconData: { [size: string]: ImageData } | null = null;
let successIconData: { [size: string]: ImageData } | null = null;

// Load an icon and convert to ImageData
async function loadIcon(path: string, size: number): Promise<ImageData> {
  const response = await fetch(chrome.runtime.getURL(path));
  const blob = await response.blob();
  const bitmap = await createImageBitmap(blob);

  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Failed to get canvas context');

  ctx.drawImage(bitmap, 0, 0, size, size);
  return ctx.getImageData(0, 0, size, size);
}

// Preload icons when service worker starts
async function preloadIcons() {
  try {
    defaultIconData = {
      '16': await loadIcon('icons/icon-16.png', 16),
      '48': await loadIcon('icons/icon-48.png', 48),
      '128': await loadIcon('icons/icon-128.png', 128)
    };

    successIconData = {
      '16': await loadIcon('icons/icon-success-16.png', 16),
      '48': await loadIcon('icons/icon-success-48.png', 48),
      '128': await loadIcon('icons/icon-success-128.png', 128)
    };

    console.log('Icons preloaded successfully');
  } catch (err) {
    console.error('Failed to preload icons:', err);
  }
}

// Preload on startup
preloadIcons();

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender) => {
  if (message.type === 'UPDATE_ICON') {
    const tabId = sender.tab?.id;
    if (!tabId) return;

    if (message.success && successIconData) {
      chrome.action.setIcon({
        tabId,
        imageData: successIconData
      }).catch(err => {
        console.error('Failed to set success icon:', err);
      });
    } else if (defaultIconData) {
      chrome.action.setIcon({
        tabId,
        imageData: defaultIconData
      }).catch(err => {
        console.error('Failed to set default icon:', err);
      });
    }
  }
});

// Listen for PING messages from the web app
chrome.runtime.onMessageExternal.addListener((message, sender, sendResponse) => {
  if (message.type === 'PING') {
    sendResponse({ type: 'PONG' });
    return true;
  }
});

export {};