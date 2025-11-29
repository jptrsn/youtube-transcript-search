<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import ChannelSearch from '$lib/components/ChannelSearch.svelte';
	import SearchResults from '$lib/components/SearchResults.svelte';
	import ProgressDisplay from '$lib/components/ProgressDisplay.svelte';

	const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

	let channel: any = null;
	let videos: any[] = [];
	let loading = true;
	let error = '';

	let searchQuery = '';
	let searchResults: any[] = [];
	let searching = false;

	let jobId = '';

	let jobProgress: any[] = [];
	let showProgress = false;

	$: channelId = $page.params.channelId;
	$: urlSearchQuery = $page.url.searchParams.get('q') || '';

	// Load channel data
	async function loadChannel() {
		console.log('loadChannel called for:', channelId);
		console.log('API_URL:', API_URL);
		loading = true;
		error = '';
		try {
			const url = `${API_URL}/api/channels/${channelId}/details`;
			console.log('Fetching:', url);
			const res = await fetch(url);
			console.log('Response status:', res.status);

			if (res.status === 404) {
				console.log('Channel not found, auto-adding...');
				await autoAddChannel();
			} else if (res.ok) {
				const data = await res.json();
				console.log('Channel data:', data);
				channel = data;  // Changed from data.channel
				videos = data.videos;
				console.log('Set channel and videos, loading should be false next');
			} else {
				throw new Error('Failed to load channel');
			}
		} catch (err: any) {
			console.error('Error in loadChannel:', err);
			error = err.message;
		} finally {
			console.log('Finally block, setting loading to false');
			loading = false;
			console.log('loading is now:', loading);
		}
	}

	async function autoAddChannel() {
    try {
        const params = new URLSearchParams({
            channel_url: `https://youtube.com/channel/${channelId}`,
            transcript_limit: '5'
        });

        const res = await fetch(`${API_URL}/api/channels/add-limited-async?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!res.ok) throw new Error('Failed to add channel');

        const data = await res.json();
        jobId = data.job_id;
        showProgress = true;

        connectWebSocket(jobId);
    } catch (err: any) {
        error = err.message;
        loading = false;
    }
	}

	async function performSearch(query: string) {
		if (!query.trim()) {
			searchResults = [];
			return;
		}

		searching = true;
		try {
			const res = await fetch(
				`${API_URL}/api/channels/${channelId}/search?q=${encodeURIComponent(query)}&limit=20`
			);
			if (!res.ok) throw new Error('Search failed');

			const data = await res.json();
			searchResults = data.results;
		} catch (err: any) {
			console.error('Search error:', err);
		} finally {
			searching = false;
		}
	}

	function handleSearch(event: CustomEvent<{ query: string }>) {
		const query = event.detail.query;
		searchQuery = query;

		// Update URL with search params
		const url = new URL(window.location.href);
		if (query) {
			url.searchParams.set('q', query);
		} else {
			url.searchParams.delete('q');
		}
		goto(url.pathname + url.search, { replaceState: true, noScroll: true });

		performSearch(query);
	}

	function connectWebSocket(jid: string) {
		const wsUrl = API_URL.replace('http', 'ws');
		const ws = new WebSocket(`${wsUrl}/api/ws/${jid}`);

		ws.onmessage = (event) => {
			const message = JSON.parse(event.data);

			if (message.event === 'progress') {
				jobProgress = [...jobProgress, message];
			} else if (message.event === 'complete') {
				jobProgress = [...jobProgress, message];
				setTimeout(() => {
					showProgress = false;
					loadChannel();
				}, 2000);
			} else if (message.event === 'error') {
				jobProgress = [...jobProgress, message];
				error = message.data.error;
				showProgress = false;
			}
		};

		ws.onerror = () => {
			error = 'WebSocket connection failed';
			showProgress = false;
		};
	}

	async function fetchMissingTranscripts() {
		try {
			const res = await fetch(`${API_URL}/api/channels/${channelId}/fetch-missing-async`, {
				method: 'POST'
			});

			if (!res.ok) throw new Error('Failed to start job');

			const data = await res.json();
			jobId = data.job_id;
			showProgress = true;

			connectWebSocket(jobId);
		} catch (err: any) {
			error = err.message;
		}
	}

	async function retryFailedTranscripts() {
		try {
			const res = await fetch(`${API_URL}/api/channels/${channelId}/retry-async`, {
				method: 'POST'
			});

			if (!res.ok) throw new Error('Failed to start job');

			const data = await res.json();
			jobId = data.job_id;
			showProgress = true;

			connectWebSocket(jobId);
		} catch (err: any) {
			error = err.message;
		}
	}

	function getStatusBadge(video: any) {
		if (video.has_transcript) {
			return { text: '✓ Transcript', class: 'badge-success' };
		} else if (video.error_type) {
			return { text: `⚠ ${video.error_type}`, class: 'badge-error' };
		} else {
			return { text: '⏳ Pending', class: 'badge-pending' };
		}
	}

	// On mount, load channel and perform search if query in URL
	onMount(() => {
		console.log('onMount called, channelId:', channelId);
		loadChannel();
		if (urlSearchQuery) {
			searchQuery = urlSearchQuery;
			performSearch(urlSearchQuery);
		}
	});

	// Watch for URL param changes (e.g., browser back/forward)
	$: if (urlSearchQuery !== searchQuery) {
		searchQuery = urlSearchQuery;
		if (urlSearchQuery) {
			performSearch(urlSearchQuery);
		} else {
			searchResults = [];
		}
	}
</script>

<div class="container">
	{#if loading}
		<div class="loading">Loading channel...</div>
	{:else if error}
		<div class="error">{error}</div>
	{:else if channel}
		<div class="channel-header">
			<h1>{channel.channel_name}</h1>
			{#if channel.description}
				<p class="description">{channel.description}</p>
			{/if}
			<div class="stats">
				<span>{channel.video_count} videos</span>
				<span class="separator">•</span>
				<span>{channel.transcript_count} transcripts</span>
				<span class="separator">•</span>
				<span>{channel.coverage_percent}% coverage</span>
			</div>
			<div class="actions">
				<button on:click={fetchMissingTranscripts} class="btn-secondary">
					Fetch Missing Transcripts
				</button>
				<button on:click={retryFailedTranscripts} class="btn-secondary">
					Retry Failed Transcripts
				</button>
			</div>
		</div>

		<ChannelSearch {searchQuery} on:search={handleSearch} />

		<SearchResults results={searchResults} loading={searching} />

		{#if !searchQuery}
			<div class="videos-section">
				<h2>All Videos ({videos.length})</h2>
				<div class="video-grid">
					{#each videos as video}
						<div class="video-card">
							<a
								href="https://youtube.com/watch?v={video.video_id}"
								target="_blank"
								class="thumbnail"
							>
								<img src={video.thumbnail_url} alt={video.title} />
							</a>
							<div class="video-info">
								<a
									href="https://youtube.com/watch?v={video.video_id}"
									target="_blank"
									class="video-title"
								>
									{video.title}
								</a>
								<div class="video-meta">
									<span class="date"
										>{new Date(video.published_at).toLocaleDateString()}</span
									>
									<span class="badge {getStatusBadge(video).class}">
										{getStatusBadge(video).text}
									</span>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}

	{#if showProgress}
		<ProgressDisplay progress={jobProgress} />
	{/if}
</div>

<style>
	.container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}

	.loading,
	.error {
		text-align: center;
		padding: 3rem;
		font-size: 1.2rem;
	}

	.loading {
		color: #d4a574;
	}

	.error {
		color: #ff6b6b;
	}

	.channel-header {
		margin-bottom: 2rem;
		padding-bottom: 2rem;
		border-bottom: 3px solid #8b4513;
	}

	h1 {
		color: #ffa500;
		font-size: 2.5rem;
		margin-bottom: 1rem;
	}

	.description {
		color: #d4a574;
		font-size: 1.1rem;
		line-height: 1.6;
		margin-bottom: 1rem;
	}

	.stats {
		color: #d4a574;
		font-size: 1rem;
		margin-bottom: 1.5rem;
	}

	.separator {
		margin: 0 0.5rem;
	}

	.actions {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.btn-secondary {
		padding: 0.75rem 1.5rem;
		background: #8b4513;
		color: #f4e4d4;
		border: 3px solid #8b4513;
		font-family: 'Courier New', monospace;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.2s;
		box-shadow: 4px 4px 0 #0f0805;
	}

	.btn-secondary:hover {
		background: #a0522d;
		border-color: #a0522d;
		transform: translate(-2px, -2px);
		box-shadow: 6px 6px 0 #0f0805;
	}

	.videos-section {
		margin-top: 3rem;
	}

	h2 {
		color: #ff8c42;
		font-size: 1.8rem;
		margin-bottom: 1.5rem;
	}

	.video-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1.5rem;
	}

	.video-card {
		background: #1a0f08;
		border: 3px solid #8b4513;
		overflow: hidden;
		transition: all 0.2s;
	}

	.video-card:hover {
		border-color: #ff8c42;
		transform: translate(-2px, -2px);
		box-shadow: 6px 6px 0 #0f0805;
	}

	.thumbnail {
		display: block;
		width: 100%;
		aspect-ratio: 16/9;
		overflow: hidden;
	}

	.thumbnail img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.video-info {
		padding: 1rem;
	}

	.video-title {
		color: #ffa500;
		text-decoration: none;
		display: block;
		margin-bottom: 0.5rem;
		font-size: 1rem;
		line-height: 1.3;
	}

	.video-title:hover {
		color: #ffb732;
		text-decoration: underline;
	}

	.video-meta {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.85rem;
	}

	.date {
		color: #d4a574;
	}

	.badge {
		padding: 0.25rem 0.5rem;
		border-radius: 3px;
		font-size: 0.75rem;
	}

	.badge-success {
		background: #2d5016;
		color: #90ee90;
	}

	.badge-error {
		background: #5c1a1a;
		color: #ff6b6b;
	}

	.badge-pending {
		background: #5c4a1a;
		color: #ffd700;
	}

	@media (max-width: 768px) {
		.container {
			padding: 1rem;
		}

		h1 {
			font-size: 1.8rem;
		}

		.video-grid {
			grid-template-columns: 1fr;
		}
	}
</style>