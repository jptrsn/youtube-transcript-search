<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let searchQuery = '';

	const dispatch = createEventDispatcher();

	let inputValue = searchQuery;

	$: inputValue = searchQuery;

	function handleSubmit() {
		dispatch('search', { query: inputValue });
	}

	function handleClear() {
		inputValue = '';
		dispatch('search', { query: '' });
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSubmit();
		}
	}
</script>

<div class="search-container">
	<div class="search-input-wrapper">
		<input
			type="text"
			bind:value={inputValue}
			on:keydown={handleKeydown}
			placeholder="Search transcripts in this channel..."
			class="search-input"
		/>
		{#if inputValue}
			<button
				on:click={handleClear}
				class="clear-button"
				type="button"
				aria-label="Clear search"
			>
				×
			</button>
		{/if}
	</div>
	<button on:click={handleSubmit} class="search-button" type="button">
		Search
	</button>
</div>

<style>
	.search-container {
		display: flex;
		gap: 1rem;
		margin: 2rem 0;
		width: 100%;
	}

	.search-input-wrapper {
		flex: 1;
		position: relative;
		display: flex;
		align-items: center;
	}

	.search-input {
		width: 100%;
		padding: 1rem;
		padding-right: 3.5rem;
		background: #1a0f08;
		color: #f4e4d4;
		border: 3px solid #8b4513;
		font-family: 'Courier New', monospace;
		font-size: 1rem;
		box-sizing: border-box;
	}

	.search-input:focus {
		outline: none;
		border-color: #ff8c42;
	}

	.clear-button {
		position: absolute;
		right: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		background: #8b4513;
		border: 2px solid #8b4513;
		color: #f4e4d4;
		font-size: 1.5rem;
		line-height: 1;
		width: 2rem;
		height: 2rem;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.2s;
		padding: 0;
		flex-shrink: 0;
	}

	.clear-button:hover {
		background: #a0522d;
		border-color: #a0522d;
		color: #fff;
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
		white-space: nowrap;
		flex-shrink: 0;
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
			gap: 0.75rem;
		}

		.search-button {
			width: 100%;
		}
	}

	@media (max-width: 480px) {
		.search-input {
			font-size: 0.9rem;
			padding: 0.875rem;
			padding-right: 3rem;
		}

		.clear-button {
			width: 1.75rem;
			height: 1.75rem;
			font-size: 1.25rem;
		}

		.search-button {
			padding: 0.875rem 1.5rem;
			font-size: 0.9rem;
		}
	}
</style>