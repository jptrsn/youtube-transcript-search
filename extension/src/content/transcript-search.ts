// Inject CSS for search UI
function injectCSS(): void {
  // Check if already injected
  if (document.getElementById('ytts-styles')) {
    return;
  }

  const link = document.createElement('link');
  link.id = 'ytts-styles';
  link.rel = 'stylesheet';
  link.href = chrome.runtime.getURL('content/transcript-search.css');
  document.head.appendChild(link);
}

// Check if search UI is already injected
export function isSearchUIInjected(): boolean {
  return document.getElementById('ytts-search-container') !== null;
}

// Inject search UI into the transcript panel
export function injectSearchUI(): void {
  // Inject CSS first
  injectCSS();

  // Prevent multiple injections
  if (isSearchUIInjected()) {
    console.log('Search UI already injected');
    return;
  }

  // Find the transcript panel header - be more specific
  const header = document.querySelector(
    'ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-searchable-transcript"] ' +
    'ytd-transcript-search-panel-renderer #header'
  );
  if (!header) {
    console.error('Could not find transcript panel header');
    return;
  }

  // Find the content area (where segments are)
  const content = document.querySelector('ytd-transcript-search-panel-renderer #body');
  if (!content) {
    console.error('Could not find transcript content area');
    return;
  }

  // Create search container
  const searchContainer = document.createElement('div');
  searchContainer.id = 'ytts-search-container';
  searchContainer.className = 'ytts-search-container';

  // Create search input
  const searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.id = 'ytts-search-input';
  searchInput.className = 'ytts-search-input';
  searchInput.placeholder = 'Search transcript...';

  // Create search button
  const searchButton = document.createElement('button');
  searchButton.id = 'ytts-search-button';
  searchButton.className = 'ytts-search-button';
  searchButton.textContent = '🔍';
  searchButton.title = 'Search';

  // Create navigation container (hidden initially)
  const navContainer = document.createElement('div');
  navContainer.id = 'ytts-nav-container';
  navContainer.className = 'ytts-nav-container';
  navContainer.style.display = 'none';

  // Create results counter
  const resultsCounter = document.createElement('span');
  resultsCounter.id = 'ytts-results-counter';
  resultsCounter.className = 'ytts-results-counter';

  // Create previous button
  const prevButton = document.createElement('button');
  prevButton.id = 'ytts-prev-button';
  prevButton.className = 'ytts-nav-button';
  prevButton.textContent = '↑';
  prevButton.title = 'Previous match';

  // Create next button
  const nextButton = document.createElement('button');
  nextButton.id = 'ytts-next-button';
  nextButton.className = 'ytts-nav-button';
  nextButton.textContent = '↓';
  nextButton.title = 'Next match';

  // Create clear button
  const clearButton = document.createElement('button');
  clearButton.id = 'ytts-clear-button';
  clearButton.className = 'ytts-clear-button';
  clearButton.textContent = '✕';
  clearButton.title = 'Clear search';

  // Assemble navigation container
  navContainer.appendChild(resultsCounter);
  navContainer.appendChild(prevButton);
  navContainer.appendChild(nextButton);
  navContainer.appendChild(clearButton);

  // Assemble search container
  searchContainer.appendChild(searchInput);
  searchContainer.appendChild(searchButton);
  searchContainer.appendChild(navContainer);

  // Insert after header
  header.insertAdjacentElement('afterend', searchContainer);

  // Add event listeners
  searchButton.addEventListener('click', () => performSearch());
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
  });
  prevButton.addEventListener('click', () => navigateMatches(-1));
  nextButton.addEventListener('click', () => navigateMatches(1));
  clearButton.addEventListener('click', () => clearSearch());

  console.log('Search UI injected successfully');
}

// Search state
let currentMatches: Element[] = [];
let currentMatchIndex = -1;

// Perform search in transcript
function performSearch(): void {
  const searchInput = document.getElementById('ytts-search-input') as HTMLInputElement;
  const query = searchInput.value.trim().toLowerCase();

  if (!query) {
    clearSearch();
    return;
  }

  // Clear previous search
  clearHighlights();

  // Find all transcript segments ONLY in the visible transcript panel
  const segments = document.querySelectorAll(
    'ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-searchable-transcript"][visibility="ENGAGEMENT_PANEL_VISIBILITY_EXPANDED"] ' +
    'ytd-transcript-segment-renderer'
  );
  currentMatches = [];

  segments.forEach((segment) => {
    const textElement = segment.querySelector('.segment-text');
    if (!textElement) return;

    const text = textElement.textContent?.toLowerCase() || '';

    if (text.includes(query)) {
      // Add yellow highlight class to matching segment
      segment.classList.add('ytts-match');
      currentMatches.push(segment);
    }
  });

  if (currentMatches.length > 0) {
    // Show navigation UI alongside search input
    const navContainer = document.getElementById('ytts-nav-container') as HTMLDivElement;
    navContainer.style.display = 'flex';

    // Highlight first match and scroll to it
    currentMatchIndex = 0;
    highlightCurrentMatch();
    updateResultsCounter();
  } else {
    alert('No matches found');
  }
}

// Navigate between matches
function navigateMatches(direction: number): void {
  if (currentMatches.length === 0) return;

  // Remove green highlight from current
  if (currentMatchIndex >= 0 && currentMatchIndex < currentMatches.length) {
    currentMatches[currentMatchIndex].classList.remove('ytts-active-match');
  }

  // Update index
  currentMatchIndex += direction;

  // Wrap around
  if (currentMatchIndex < 0) {
    currentMatchIndex = currentMatches.length - 1;
  } else if (currentMatchIndex >= currentMatches.length) {
    currentMatchIndex = 0;
  }

  highlightCurrentMatch();
  updateResultsCounter();
}

// Highlight the current match
function highlightCurrentMatch(): void {
  if (currentMatchIndex < 0 || currentMatchIndex >= currentMatches.length) return;

  const currentMatch = currentMatches[currentMatchIndex];
  currentMatch.classList.add('ytts-active-match');

  // Scroll to the match
  currentMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Update results counter display
function updateResultsCounter(): void {
  const counter = document.getElementById('ytts-results-counter') as HTMLSpanElement;
  if (counter) {
    counter.textContent = `${currentMatchIndex + 1} / ${currentMatches.length}`;
  }
}

// Clear search and restore UI
function clearSearch(): void {
  clearHighlights();

  // Reset state
  currentMatches = [];
  currentMatchIndex = -1;

  // Hide navigation UI and clear input
  const navContainer = document.getElementById('ytts-nav-container') as HTMLDivElement;
  const searchInput = document.getElementById('ytts-search-input') as HTMLInputElement;

  if (searchInput) {
    searchInput.value = '';
  }
  if (navContainer) navContainer.style.display = 'none';
}

// Clear all highlight classes
function clearHighlights(): void {
  const allMatches = document.querySelectorAll('.ytts-match, .ytts-active-match');
  allMatches.forEach((element) => {
    element.classList.remove('ytts-match', 'ytts-active-match');
  });
}

// Open search UI with optional query
export async function openSearchUI(query?: string): Promise<void> {
  // Inject UI if not already present
  if (!isSearchUIInjected()) {
    // Wait a bit for panel to fully render
    await new Promise(resolve => setTimeout(resolve, 500));
    injectSearchUI();
  }

  // If query provided, perform search
  if (query) {
    const searchInput = document.getElementById('ytts-search-input') as HTMLInputElement;
    if (searchInput) {
      searchInput.value = query;
      performSearch();
    }
  }
}