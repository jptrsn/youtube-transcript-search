/* eslint-disable @typescript-eslint/no-explicit-any */

const EXTENSION_ID = import.meta.env.PUBLIC_CHROME_EXTENSION_ID;

export async function requestTranscriptFetch(videoId: string): Promise<{success: boolean, message?: string}> {
	return new Promise((resolve) => {
		const browserAPI = (typeof chrome !== 'undefined' && chrome.runtime)
			? chrome
			: (typeof browser !== 'undefined' && browser.runtime)
				? browser
				: null;

		if (!browserAPI) {
			resolve({ success: false, message: 'Browser API not available' });
			return;
		}

		try {
			browserAPI.runtime.sendMessage(
				EXTENSION_ID,
				{
					type: 'FETCH_TRANSCRIPT',
					videoId
				},
				(response: any) => {
					if (browserAPI.runtime.lastError) {
						resolve({ success: false, message: browserAPI.runtime.lastError.message });
					} else if (response?.success) {
						resolve({ success: true });
					} else {
						resolve({ success: false, message: response?.message || 'Unknown error' });
					}
				}
			);
		} catch (err) {
			resolve({ success: false, message: String(err) });
		}
	});
}