<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let searchQuery = '';

	const dispatch = createEventDispatcher();

	let inputValue = searchQuery;

	// Sync with parent query
	$: inputValue = searchQuery;

	function handleSubmit() {
		dispatch('search', { query: inputValue });
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSubmit();
		}
	}
</script>

<div class="search-container">
	<input
		type="text"
		bind:value={inputValue}
		on:keydown={handleKeydown}
		placeholder="Search transcripts in this channel..."
		class="search-input"
	/>
	<button on:click={handleSubmit} class="search-button">Search</button>
</div>

<style>
	.search-container {
		display: flex;
		gap: 1rem;
		margin: 2rem 0;
	}

	.search-input {
		flex: 1;
		padding: 1rem;
		background: #1a0f08;
		color: #f4e4d4;
		border: 3px solid #8b4513;
		font-family: 'Courier New', monospace;
		font-size: 1rem;
	}

	.search-input:focus {
		outline: none;
		border-color: #ff8c42;
	}

	.search-button {
		padding: 1rem 2rem;
		background: #ff8c42;
		color: #1a0f08;
		border: 3px solid #ff8c42;
		font-family: 'Courier New', monospace;
		font-size: 1rem;
		font-weight: bold;
		cursor: pointer;
		transition: all 0.2s;
		box-shadow: 4px 4px 0 #0f0805;
	}

	.search-button:hover {
		background: #ffa500;
		border-color: #ffa500;
		transform: translate(-2px, -2px);
		box-shadow: 6px 6px 0 #0f0805;
	}

	@media (max-width: 768px) {
		.search-container {
			flex-direction: column;
		}
	}
</style>