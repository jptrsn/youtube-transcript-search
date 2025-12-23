/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./src/config.ts":
/*!***********************!*\
  !*** ./src/config.ts ***!
  \***********************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   API_URL: () => (/* binding */ API_URL)
/* harmony export */ });
const API_URL = "http://localhost:8000" || 0;


/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/************************************************************************/
var __webpack_exports__ = {};
// This entry needs to be wrapped in an IIFE because it needs to be isolated against other modules in the chunk.
(() => {
/*!****************************!*\
  !*** ./src/popup/popup.ts ***!
  \****************************/
__webpack_require__.r(__webpack_exports__);
/* harmony import */ var _config__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../config */ "./src/config.ts");

const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const message = document.getElementById('message');
// Get current tab's channel ID
async function getCurrentChannelId() {
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
        /youtube\.com\/watch\?v=([^&]+)/ // We'll need to resolve this
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
                return await getChannelFromTab(tab.id);
            }
            return identifier;
        }
    }
    return null;
}
// Resolve handle to channel ID
async function resolveHandle(handle) {
    try {
        const response = await fetch(`${_config__WEBPACK_IMPORTED_MODULE_0__.API_URL}/api/channels/resolve-handle/${handle}`);
        if (!response.ok)
            return null;
        const data = await response.json();
        return data.channel_id;
    }
    catch (e) {
        console.error('Error resolving handle:', e);
        return null;
    }
}
// Get channel ID from the current tab's page
async function getChannelFromTab(tabId) {
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
    }
    catch (e) {
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
    const searchUrl = `${_config__WEBPACK_IMPORTED_MODULE_0__.API_URL}/channel/${channelId}?q=${encodeURIComponent(query)}`;
    chrome.tabs.create({ url: searchUrl });
    // Close popup
    window.close();
}
// Show message to user
function showMessage(text, isError = false) {
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

})();

/******/ })()
;