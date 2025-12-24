import { API_URL } from '../config';

// State
interface PopupState {
  isOnVideoPage: boolean;
  videoId: string | null;
  hasTranscript: boolean;
  hasInPageSearch: boolean;
  isLoading: boolean;
}

let state: PopupState = {
  isOnVideoPage: false,
  videoId: null,
  hasTranscript: false,
  hasInPageSearch: false,
  isLoading: true
};

// DOM elements
const searchInput = document.getElementById('searchInput') as HTMLInputElement;
const searchButton = document.getElementById('searchButton') as HTMLButtonElement;
const messageDiv = document.getElementById('message') as HTMLDivElement;
const resultsDiv = document.getElementById('results') as HTMLDivElement;
const searchForm = document.querySelector('.search-form') as HTMLDivElement;

// Extract video ID from current tab
async function getVideoId(): Promise<string | null> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab.url) return null;

  const match = tab.url.match(/youtube\.com\/watch\?v=([^&]+)/);
  return match ? match[1] : null;
}

// Check if video has transcript via API
async function checkTranscriptStatus(videoId: string): Promise<boolean> {
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'FETCH_DATA',
      url: `${API_URL}/api/videos/${videoId}/exists`
    });

    if (response.error) {
      throw new Error(response.error);
    }

    return response.has_transcript === true;
  } catch (e) {
    console.error('Error checking transcript status:', e);
    return false;
  }
}

// Check if in-page search UI already exists
async function checkInPageSearchExists(tabId: number): Promise<boolean> {
  try {
    const response = await chrome.tabs.sendMessage(tabId, {
      type: 'CHECK_IN_PAGE_SEARCH_UI'
    });

    return response?.exists === true;
  } catch (e) {
    // Content script might not be ready yet
    return false;
  }
}

// Initialize popup state
async function initializePopup() {
  state.isLoading = true;
  updateUI();

  const videoId = await getVideoId();

  if (!videoId) {
    state.isOnVideoPage = false;
    state.isLoading = false;
    updateUI();
    return;
  }

  state.isOnVideoPage = true;
  state.videoId = videoId;

  // Check transcript status
  const hasTranscript = await checkTranscriptStatus(videoId);
  state.hasTranscript = hasTranscript;

  if (hasTranscript) {
    // Check if in-page search exists
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab.id) {
      const hasInPageSearch = await checkInPageSearchExists(tab.id);
      state.hasInPageSearch = hasInPageSearch;
    }
  }

  state.isLoading = false;
  updateUI();
}

// Update UI based on current state
function updateUI() {
  // Clear results
  resultsDiv.innerHTML = '';

  if (state.isLoading) {
    showMessage('Loading...');
    searchForm.style.display = 'none';
    removeAddInPageButton();
    return;
  }

  if (!state.isOnVideoPage) {
    showMessage('Navigate to a YouTube video to search its transcript.');
    searchForm.style.display = 'none';
    removeAddInPageButton();
    return;
  }

  if (!state.hasTranscript) {
    showMessage('This video does not have a transcript available.', true);
    searchForm.style.display = 'none';
    removeAddInPageButton();
    return;
  }

  // Has transcript - show search form
  searchForm.style.display = 'flex';
  searchInput.placeholder = 'Search this video\'s transcript...';
  searchButton.innerHTML = '🔍'; // Magnifying glass icon
  searchButton.title = 'Search in Popup'; // Tooltip for accessibility

  // Show/hide "Add Search In Page" button
  if (!state.hasInPageSearch) {
    addAddInPageButton();
  } else {
    removeAddInPageButton();
  }

  showMessage('');
}

// Add "Add Search In Page" button
function addAddInPageButton() {
  let addInPageBtn = document.getElementById('addInPageButton') as HTMLButtonElement;

  if (!addInPageBtn) {
    addInPageBtn = document.createElement('button');
    addInPageBtn.id = 'addInPageButton';
    addInPageBtn.className = 'secondary-button';
    addInPageBtn.textContent = 'Add Search In Page';
    addInPageBtn.addEventListener('click', addInPageSearch);
    searchForm.insertAdjacentElement('afterend', addInPageBtn);
  }
}

// Remove "Add Search In Page" button
function removeAddInPageButton() {
  const addInPageBtn = document.getElementById('addInPageButton');
  if (addInPageBtn) {
    addInPageBtn.remove();
  }
}

// Perform search in popup (Mode 1)
async function performPopupSearch() {
  const query = searchInput.value.trim();

  if (!query) {
    showMessage('Please enter a search query', true);
    return;
  }

  showMessage('Searching...');

  // TODO: Will implement in popup-search.ts next
  showMessage('Popup search not yet implemented', true);
}

// Add in-page search UI (Mode 2)
async function addInPageSearch() {
  const query = searchInput.value.trim();

  showMessage('Adding search to page...');

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab.id) {
    showMessage('Error: Cannot communicate with page', true);
    return;
  }

  try {
    const response = await chrome.tabs.sendMessage(tab.id, {
      type: 'OPEN_IN_PAGE_SEARCH',
      query: query || undefined
    });

    if (response?.success) {
      // Close popup on success
      window.close();
    } else {
      showMessage(response?.error || 'Failed to add search UI', true);
    }
  } catch (e) {
    showMessage(`Error: ${e}`, true);
  }
}

// Show message to user
function showMessage(text: string, isError: boolean = false) {
  messageDiv.textContent = text;
  messageDiv.className = isError ? 'message error' : 'message';
}

// Event listeners
searchButton.addEventListener('click', performPopupSearch);
searchInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    performPopupSearch();
  }
});

// Initialize on load
initializePopup();

export {};