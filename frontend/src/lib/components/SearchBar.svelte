<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let loading = false;

	let searchInput = '';
	const dispatch = createEventDispatcher();

	function handleSubmit() {
		if (searchInput.trim()) {
			dispatch('search', searchInput);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			handleSubmit();
		}
	}
</script>

<div class="search-container">
	<div class="search-box">
		<input
			type="text"
			bind:value={searchInput}
			on:keydown={handleKeydown}
			placeholder="Enter a phrase or word..."
			disabled={loading}
			class="search-input"
		/>
		<button on:click={handleSubmit} disabled={loading} class="search-button">
			{loading ? 'Searching...' : 'Search'}
		</button>
	</div>
</div>

<style>
	.search-container {
		margin-bottom: 2rem;
	}

	.search-box {
		display: flex;
		gap: 0.5rem;
		box-shadow: 8px 8px 0 #1a0f08;
	}

	.search-input {
		flex: 1;
		padding: 1rem 1.5rem;
		font-size: 1.1rem;
		font-family: 'Courier New', monospace;
		background: #1a0f08;
		color: #f4e4d4;
		border: 3px solid #ff8c42;
		border-radius: 0;
		outline: none;
	}

	.search-input::placeholder {
		color: #8b7355;
	}

	.search-input:focus {
		border-color: #ffa500;
		background: #241610;
	}

	.search-button {
		padding: 1rem 2rem;
		font-size: 1.1rem;
		font-family: 'Courier New', monospace;
		font-weight: bold;
		background: #ff8c42;
		color: #1a0f08;
		border: 3px solid #ff8c42;
		cursor: pointer;
		transition: all 0.2s;
		border-radius: 0;
	}

	.search-button:hover:not(:disabled) {
		background: #ffa500;
		border-color: #ffa500;
		transform: translate(-2px, -2px);
	}

	.search-button:active:not(:disabled) {
		transform: translate(0, 0);
	}

	.search-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	@media (max-width: 768px) {
		.search-box {
			flex-direction: column;
			gap: 0.75rem;
		}

		.search-input,
		.search-button {
			width: 100%;
		}
	}
</style>