<script lang="ts">
	import { onMount } from 'svelte';
	import SearchBar from '$lib/components/SearchBar.svelte';
	import SearchResults from '$lib/components/SearchResults.svelte';
	import ChannelFilter from '$lib/components/ChannelFilter.svelte';
	import { PUBLIC_API_URL } from '$env/static/public';

	let query = '';
	let results: any[] = [];
	let filteredResults: any[] = [];
	let loading = false;
	let error = '';
	let searchCount = 0;
	let enabledChannels: Set<string> = new Set();

	$: {
		// Get unique channels from results
		const channels = new Set(results.map((r) => r.channel_name));

		// Initialize all channels as enabled if not already set
		if (results.length > 0 && enabledChannels.size === 0) {
			enabledChannels = new Set(channels);
		}

		// Filter results based on enabled channels
		filteredResults = results.filter((r) => enabledChannels.has(r.channel_name));
	}

	async function handleSearch(searchQuery: string) {
		if (!searchQuery.trim()) return;

		query = searchQuery;
		loading = true;
		error = '';
		enabledChannels = new Set(); // Reset filters on new search

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

	function handleChannelToggle(event: CustomEvent<{ channel: string; enabled: boolean }>) {
		const { channel, enabled } = event.detail;

		if (enabled) {
			enabledChannels.add(channel);
		} else {
			enabledChannels.delete(channel);
		}

		// Create a new Set to trigger reactivity
		enabledChannels = new Set(enabledChannels);
	}

	// Get channel stats for filter
	function getChannelStats() {
		const stats = new Map<string, number>();
		results.forEach((r) => {
			stats.set(r.channel_name, (stats.get(r.channel_name) || 0) + 1);
		});
		return Array.from(stats.entries()).map(([name, count]) => ({
			name,
			count,
			enabled: enabledChannels.has(name)
		}));
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
			<a href="/channels" class="channels-link">Manage Channels →</a>
		</header>

		<SearchBar on:search={(e) => handleSearch(e.detail)} {loading} />

		{#if error}
			<div class="error">{error}</div>
		{/if}

		{#if query && !loading && results.length > 0}
			<div class="results-layout">
				<aside class="filters">
					<ChannelFilter
						channels={getChannelStats()}
						on:toggle={handleChannelToggle}
					/>
				</aside>
				<div class="results-content">
					<div class="results-info">
						Showing {filteredResults.length} of {searchCount} result{searchCount !== 1 ? 's' : ''} for "{query}"
					</div>
					<SearchResults results={filteredResults} {loading} />
				</div>
			</div>
		{:else if query && !loading && results.length === 0}
			<div class="results-info">
				Found 0 results for "{query}"
			</div>
		{/if}
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
		max-width: 1400px;
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

	.channels-link {
		display: block;
		text-align: center;
		color: #d4a574;
		text-decoration: none;
		font-size: 1rem;
		margin-top: 1rem;
	}

	.channels-link:hover {
		color: #ff8c42;
	}

	.error {
		background: #8b0000;
		color: #fff;
		padding: 1rem;
		border-radius: 4px;
		margin: 1rem 0;
		border: 2px solid #ff6b6b;
	}

	.results-layout {
		display: grid;
		grid-template-columns: 250px 1fr;
		gap: 2rem;
		margin-top: 1.5rem;
	}

	.filters {
		position: sticky;
		top: 2rem;
		align-self: start;
	}

	.results-content {
		min-width: 0;
	}

	.results-info {
		color: #d4a574;
		margin: 1.5rem 0 1rem 0;
		font-size: 0.95rem;
	}

	@media (max-width: 768px) {
		h1 {
			font-size: 2rem;
		}

		.tagline {
			font-size: 1rem;
		}

		.results-layout {
			grid-template-columns: 1fr;
		}

		.filters {
			position: static;
			margin-bottom: 1rem;
		}
	}
</style>