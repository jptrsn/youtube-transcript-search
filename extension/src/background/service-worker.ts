// Background service worker - handles icon updates

const ICONS = {
  default: {
    '16': 'icons/icon-16.png',
    '48': 'icons/icon-48.png',
    '128': 'icons/icon-128.png'
  },
  success: {
    '16': 'icons/icon-success-16.png',
    '48': 'icons/icon-success-48.png',
    '128': 'icons/icon-success-128.png'
  }
};

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender) => {
  if (message.type === 'UPDATE_ICON') {
    const tabId = sender.tab?.id;
    if (!tabId) return;

    if (message.success) {
      // Show success icon
      chrome.action.setIcon({
        tabId,
        path: ICONS.success
      });
    } else {
      // Reset to default icon
      chrome.action.setIcon({
        tabId,
        path: ICONS.default
      });
    }
  }
});

export {};