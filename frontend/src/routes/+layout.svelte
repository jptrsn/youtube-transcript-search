<script lang="ts">
	import { onMount } from 'svelte';
	import { extensionInstalled, extensionChecked } from '$lib/stores/extension';


	const EXTENSION_ID = import.meta.env.PUBLIC_CHROME_EXTENSION_ID;
	// For Firefox, you'll use a different ID format when you publish

	onMount(() => {
		// Cross-browser extension API (chrome/browser)
		const browserAPI = (typeof chrome !== 'undefined' && chrome.runtime)
			? chrome
			: (typeof browser !== 'undefined' && browser.runtime)
				? browser
				: null;

		if (!browserAPI) {
			// No extension API available (not Chrome/Firefox/Edge)
			extensionInstalled.set(false);
			extensionChecked.set(true);
			return;
		}

		try {
			browserAPI.runtime.sendMessage(
				EXTENSION_ID,
				{ type: 'PING' },
				(response: any) => {
					const lastError = browserAPI.runtime.lastError;
					if (lastError) {
						// Extension not installed or not responding
						extensionInstalled.set(false);
					} else if (response?.type === 'PONG') {
						// Extension installed and responding
						extensionInstalled.set(true);
					} else {
						extensionInstalled.set(false);
					}
					extensionChecked.set(true);
				}
			);
		} catch (err) {
			extensionInstalled.set(false);
			extensionChecked.set(true);
		}
	});
</script>

<slot />

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		background: #2a1810;
		color: #f4e4d4;
		font-family: 'Courier New', monospace;
		min-height: 100vh;
	}
</style>