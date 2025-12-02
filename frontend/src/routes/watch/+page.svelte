<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

	const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

	let video: any = null;
	let matches: any[] = [];
	let loading = true;
	let error = '';

	$: videoId = $page.url.searchParams.get('v');
	$: searchQuery = $page.url.searchParams.get('q') || '';

	async function loadVideo() {
		if (!videoId) {
			error = 'No video ID provided';
			loading = false;
			return;
		}

		loading = true;
		error = '';

		try {
			const params = new URLSearchParams({ v: videoId });
			if (searchQuery) {
				params.append('q', searchQuery);
			}

			const res = await fetch(`${API_URL}/api/videos/${videoId}/details?${params}`);

			if (res.status === 404) {
				error = 'Video not found in our database';
			} else if (res.ok) {
				const data = await res.json();
				video = data;
				matches = data.matches || [];
			} else {
				throw new Error('Failed to load video');
			}
		} catch (err: any) {
			console.error('Error loading video:', err);
			error = err.message;
		} finally {
			loading = false;
		}
	}

	function formatTimestamp(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const mins = Math.floor((seconds % 3600) / 60);
		const secs = Math.floor(seconds % 60);

		if (hours > 0) {
			return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
		}
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	onMount(() => {
		loadVideo();
	});

	$: if (videoId || searchQuery) {
		loadVideo();
	}

  let searchInput = '';

  $: searchInput = searchQuery;

  function handleSearch() {
    const url = new URL(window.location.href);
    if (searchInput.trim()) {
      url.searchParams.set('q', searchInput.trim());
    } else {
      url.searchParams.delete('q');
    }
    goto(url.pathname + url.search, { replaceState: false, noScroll: true });
  }

  function handleClearSearch() {
    searchInput = '';
    const url = new URL(window.location.href);
    url.searchParams.delete('q');
    goto(url.pathname + url.search, { replaceState: true, noScroll: true });
  }

  function handleSearchKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }
</script>

<svelte:head>
	<title>{video ? video.title : 'Video'} - YouTube Transcript Search</title>
</svelte:head>

<div class="container">
	{#if loading}
		<div class="loading">Loading video...</div>
	{:else if error}
		<div class="error-container">
			<div class="error">{error}</div>
			{#if videoId}
				<a href="https://youtube.com/watch?v={videoId}" target="_blank" class="youtube-link">
					Watch on YouTube instead
				</a>
			{/if}
		</div>
	{:else if video}
		<div class="video-header">
			<a href="/channel/{video.channel.channel_id}" class="back-link">← Back to {video.channel.channel_name}</a>

			<h1>{video.title}</h1>

			<div class="video-meta">
        <a
					href="/channel/{video.channel.channel_id}"
					class="channel-link"
				>
					{video.channel.channel_name}
				</a>
				<span class="separator">•</span>
				<span class="date">{new Date(video.published_at).toLocaleDateString()}</span>
				<span class="separator">•</span>
        <a
					href="https://youtube.com/watch?v={video.video_id}"
					target="_blank"
					class="youtube-link"
				>
					Watch on YouTube
				</a>
			</div>

			{#if video.description}
        <details class="description-details">
          <summary class="description-summary">
            <span class="description-preview">{video.description}</span>
          </summary>
          <p class="description-full">{video.description}</p>
        </details>
      {/if}
		</div>

    {#if video.has_transcript}
			<div class="search-container">
				<div class="search-input-wrapper">
					<input
						type="text"
						bind:value={searchInput}
						on:keydown={handleSearchKeydown}
						placeholder="Search within this video's transcript..."
						class="search-input"
					/>
					{#if searchInput}
						<button
							on:click={handleClearSearch}
							class="clear-button"
							type="button"
							aria-label="Clear search"
						>
							×
						</button>
					{/if}
				</div>
				<button on:click={handleSearch} class="search-button" type="button">
					Search
				</button>
			</div>
		{/if}

		{#if !video.has_transcript}
      <div class="no-transcript">
        <p>No transcript available for this video.</p>
      </div>
    {:else if searchQuery && matches.length > 0}
      <div class="matches-section">
        <h2>Found {matches.length} {matches.length === 1 ? 'match' : 'matches'} for "{searchQuery}"</h2>

        <div class="matches-list">
          {#each matches as match}
            <div class="match-item">
              <a
                href="https://youtube.com/watch?v={video.video_id}&t={Math.floor(match.timestamp)}s"
                target="_blank"
                class="timestamp"
              >
                {formatTimestamp(match.timestamp)}
              </a>
              <div class="match-text">
                {@html match.text}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {:else if searchQuery}
      <div class="no-matches">
        <p>No matches found for "{searchQuery}" in this video's transcript.</p>
      </div>
    {:else if video.transcript}
      <div class="transcript-section">
        <h2>Full Transcript</h2>

        <div class="transcript-list">
          {#each video.transcript as segment}
            <div class="transcript-item">
              <a
                href="https://youtube.com/watch?v={video.video_id}&t={Math.floor(segment.start)}s"
                target="_blank"
                class="timestamp"
              >
                {formatTimestamp(segment.start)}
              </a>
              <div class="transcript-text">
                {segment.text}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
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
		color: #d4a574;
	}

	.error-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	.error {
		color: #ff6b6b;
	}

	.video-header {
		margin-bottom: 3rem;
		padding-bottom: 2rem;
		border-bottom: 3px solid #8b4513;
	}

	.back-link {
		color: #d4a574;
		text-decoration: none;
		font-size: 1.1rem;
		display: inline-block;
		margin-bottom: 2rem;
	}

	.back-link:hover {
		color: #ff8c42;
	}

	h1 {
		color: #ffa500;
		font-size: 2.5rem;
		margin-bottom: 1rem;
	}

	.video-meta {
		color: #d4a574;
		font-size: 1rem;
		margin-bottom: 1rem;
	}

	.separator {
		margin: 0 0.5rem;
	}

	.channel-link,
	.youtube-link {
		color: #ff8c42;
		text-decoration: none;
	}

	.channel-link:hover,
	.youtube-link:hover {
		text-decoration: underline;
	}

	.no-transcript,
	.no-matches {
		text-align: center;
		padding: 3rem;
		color: #d4a574;
		background: #1a0f08;
		border: 3px solid #8b4513;
	}

	.matches-section {
		margin-top: 2rem;
	}

	h2 {
		color: #ff8c42;
		font-size: 1.8rem;
		margin-bottom: 1.5rem;
	}

	.matches-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.match-item {
		display: flex;
		gap: 1.5rem;
		padding: 1rem;
		background: #1a0f08;
		border: 3px solid #8b4513;
		transition: all 0.2s;
	}

	.match-item:hover {
		border-color: #ff8c42;
		transform: translate(-2px, -2px);
		box-shadow: 4px 4px 0 #0f0805;
	}

	.timestamp {
		color: #ff8c42;
		text-decoration: none;
		font-weight: bold;
		font-family: 'Courier New', monospace;
		flex-shrink: 0;
		min-width: 80px;
	}

	.timestamp:hover {
		text-decoration: underline;
	}

	.match-text {
		color: #d4a574;
		line-height: 1.6;
		flex: 1;
	}

	.match-text :global(mark) {
		background: #ff8c42;
		color: #1a0f08;
		padding: 0.1rem 0.3rem;
		font-weight: bold;
	}

  .transcript-section {
	margin-top: 2rem;
}

.transcript-list {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
}

.transcript-item {
	display: flex;
	gap: 1.5rem;
	padding: 0.75rem;
	background: #1a0f08;
	border-left: 3px solid #8b4513;
	transition: all 0.2s;
}

.transcript-item:hover {
	border-left-color: #ff8c42;
	background: #221508;
}

.transcript-text {
	color: #d4a574;
	line-height: 1.6;
	flex: 1;
}

.description-details {
	margin-top: 1rem;
	color: #d4a574;
}

.description-summary {
	cursor: pointer;
	list-style: none;
	position: relative;
}

.description-summary::-webkit-details-marker {
	display: none;
}

.description-summary::after {
	content: 'Show more';
	color: #ff8c42;
	font-size: 0.9rem;
	margin-left: 0.5rem;
}

.description-details[open] .description-summary::after {
	content: 'Show less';
}

.description-summary:hover::after {
	color: #ffa500;
	text-decoration: underline;
}

.description-preview {
	display: -webkit-box;
	-webkit-line-clamp: 3;
  line-clamp: 3;
	-webkit-box-orient: vertical;
	overflow: hidden;
	line-height: 1.6;
	white-space: pre-wrap;
}

.description-details[open] .description-preview {
	display: none;
}

.description-full {
	margin-top: 0.5rem;
	line-height: 1.6;
	white-space: pre-wrap;
}

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

	@media (max-width: 768px) {
		.container {
			padding: 1rem;
		}

		h1 {
			font-size: 1.8rem;
		}

		.match-item {
			flex-direction: column;
			gap: 0.5rem;
		}

		.timestamp {
			min-width: auto;
		}
	}
</style>