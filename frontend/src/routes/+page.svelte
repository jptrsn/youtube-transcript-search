<script lang="ts">
	import { onMount } from 'svelte';
	import SearchBar from '$lib/components/SearchBar.svelte';
	import SearchResults from '$lib/components/SearchResults.svelte';
	import { PUBLIC_API_URL } from '$env/static/public';

	let query = '';
	let results: any[] = [];
	let loading = false;
	let error = '';
	let searchCount = 0;

	async function handleSearch(searchQuery: string) {
		if (!searchQuery.trim()) return;

		query = searchQuery;
		loading = true;
		error = '';

		try {
			const response = await fetch(
				`${PUBLIC_API_URL}/api/search?q=${encodeURIComponent(searchQuery)}&limit=20`
			);

			if (!response.ok) {
				throw new Error('Search failed');
			}

			const data = await response.json();
			results = data.results;
			searchCount = data.count;
		} catch (e) {
			error = 'Failed to search. Make sure the API is running.';
			console.error(e);
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>YouTube Transcript Search</title>
</svelte:head>

<main>
	<div class="container">
		<header>
			<h1>YouTube Transcript Search</h1>
			<p class="tagline">Find that video you're thinking of</p>
		</header>

		<SearchBar on:search={(e) => handleSearch(e.detail)} {loading} />

		{#if error}
			<div class="error">{error}</div>
		{/if}

		{#if query && !loading}
			<div class="results-info">
				Found {searchCount} result{searchCount !== 1 ? 's' : ''} for "{query}"
			</div>
		{/if}

		<SearchResults {results} {loading} />
	</div>
</main>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		background: #2a1810;
		color: #f4e4d4;
		font-family: 'Courier New', monospace;
		min-height: 100vh;
	}

	main {
		padding: 2rem 1rem;
	}

	.container {
		max-width: 900px;
		margin: 0 auto;
	}

	header {
		text-align: center;
		margin-bottom: 3rem;
	}

	h1 {
		font-size: 3rem;
		margin: 0;
		color: #ff8c42;
		text-shadow: 3px 3px 0 #8b4513;
		letter-spacing: -2px;
	}

	.tagline {
		color: #d4a574;
		font-size: 1.1rem;
		margin-top: 0.5rem;
	}

	.error {
		background: #8b0000;
		color: #fff;
		padding: 1rem;
		border-radius: 4px;
		margin: 1rem 0;
		border: 2px solid #ff6b6b;
	}

	.results-info {
		color: #d4a574;
		margin: 1.5rem 0 1rem 0;
		font-size: 0.95rem;
	}
</style>