<script lang="ts">
	import { extensionInstalled, extensionChecked } from '$lib/stores/extension';

	export let variant: 'banner' | 'card' = 'banner';
	export let message = 'Want to add transcripts on the fly?';

	const CHROME_EXTENSION_ID = import.meta.env.PUBLIC_CHROME_EXTENSION_ID;

	const CHROME_EXTENSION_URL = `https://chrome.google.com/webstore/detail/${CHROME_EXTENSION_ID}`;
</script>

{#if $extensionChecked && !$extensionInstalled}
	<div class="extension-prompt {variant}">
		<div class="prompt-icon">🚀</div>
		<div class="prompt-content">
			<h3>{message}</h3>
			<p>
				Install our browser extension to instantly add transcripts from any YouTube video.
				Search thousands of videos in seconds—no manual indexing required.
			</p>
			<a href={CHROME_EXTENSION_URL} target="_blank" class="install-button">
				Install Extension
			</a>
		</div>
	</div>
{/if}

<style>
	.extension-prompt {
		background: linear-gradient(135deg, #ff8c42 0%, #ffa500 100%);
		color: #1a0f08;
		padding: 2rem;
		border: 3px solid #ff8c42;
		box-shadow: 6px 6px 0 #0f0805;
		display: flex;
		gap: 1.5rem;
		align-items: center;
	}

	.extension-prompt.card {
		flex-direction: column;
		text-align: center;
		max-width: 500px;
		margin: 2rem auto;
	}

	.prompt-icon {
		font-size: 3rem;
		flex-shrink: 0;
	}

	.prompt-content {
		flex: 1;
	}

	.extension-prompt.card .prompt-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	h3 {
		margin: 0 0 0.5rem 0;
		font-size: 1.5rem;
		color: #1a0f08;
	}

	p {
		margin: 0 0 1rem 0;
		line-height: 1.6;
		color: #2a1810;
	}

	.install-button {
		display: inline-block;
		padding: 0.75rem 2rem;
		background: #1a0f08;
		color: #ff8c42;
		text-decoration: none;
		font-weight: bold;
		border: 3px solid #1a0f08;
		transition: all 0.2s;
		box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
	}

	.install-button:hover {
		background: #2a1810;
		border-color: #2a1810;
		transform: translate(-2px, -2px);
		box-shadow: 5px 5px 0 rgba(0, 0, 0, 0.3);
	}

	@media (max-width: 768px) {
		.extension-prompt.banner {
			flex-direction: column;
			text-align: center;
		}

		h3 {
			font-size: 1.2rem;
		}

		p {
			font-size: 0.9rem;
		}
	}
</style>