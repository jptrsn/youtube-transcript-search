<script lang="ts">
	export let results: any[] = [];
	export let loading = false;

	function formatTimestamp(seconds: number | null): string {
		if (seconds === null) return '';
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	function getYouTubeUrl(videoId: string, timestamp: number | null): string {
		const baseUrl = `https://youtube.com/watch?v=${videoId}`;
		if (timestamp !== null) {
			// Start 3 seconds before the match for context
			const adjustedTimestamp = Math.max(0, Math.floor(timestamp) - 3);
			return `${baseUrl}&t=${adjustedTimestamp}s`;
		}
		return baseUrl;
	}

	function getMatchBadge(matchType: string): string {
		switch (matchType) {
			case 'transcript':
				return '📝 Transcript';
			case 'title':
				return '📺 Title';
			case 'description':
				return '📄 Description';
			default:
				return matchType;
		}
	}
</script>

<div class="results-container">
	{#if loading}
		<div class="loading">Searching transcripts...</div>
	{:else if results.length > 0}
		{#each results as result, i}
			<article class="result-card">
				<div class="result-number">{i + 1}</div>
				<div class="result-content">
					<a href={getYouTubeUrl(result.video_id, result.timestamp)} target="_blank" class="title">
						{result.title}
					</a>
					<div class="meta">
						<span class="channel">{result.channel_name}</span>
						<span class="separator">•</span>
						<span class="match-type">{getMatchBadge(result.match_type)}</span>
						{#if result.timestamp !== null}
							<span class="separator">•</span>
							<span class="timestamp">{formatTimestamp(result.timestamp)}</span>
						{/if}
					</div>
					<p class="snippet">{result.snippet}</p>
          <a
						href={getYouTubeUrl(result.video_id, result.timestamp)}
						target="_blank"
						class="watch-link"
					>
						Watch on YouTube →
					</a>
				</div>
			</article>
		{/each}
	{/if}
</div>

<style>
	.results-container {
		margin-top: 2rem;
	}

	.loading {
		text-align: center;
		padding: 3rem;
		color: #d4a574;
		font-size: 1.2rem;
	}

	.result-card {
		display: flex;
		gap: 1.5rem;
		background: #1a0f08;
		border: 3px solid #8b4513;
		padding: 1.5rem;
		margin-bottom: 1.5rem;
		box-shadow: 6px 6px 0 #0f0805;
		transition: all 0.2s;
	}

	.result-card:hover {
		border-color: #ff8c42;
		transform: translate(-2px, -2px);
		box-shadow: 8px 8px 0 #0f0805;
	}

	.result-number {
		font-size: 2rem;
		font-weight: bold;
		color: #ff8c42;
		min-width: 3rem;
		text-align: center;
	}

	.result-content {
		flex: 1;
	}

	.title {
		font-size: 1.3rem;
		color: #ffa500;
		text-decoration: none;
		display: block;
		margin-bottom: 0.5rem;
		line-height: 1.3;
	}

	.title:hover {
		color: #ffb732;
		text-decoration: underline;
	}

	.meta {
		color: #d4a574;
		font-size: 0.9rem;
		margin-bottom: 0.75rem;
	}

	.separator {
		margin: 0 0.5rem;
	}

	.channel {
		color: #ff8c42;
	}

	.match-type,
	.timestamp {
		color: #d4a574;
	}

	.snippet {
		color: #f4e4d4;
		line-height: 1.6;
		margin: 0.75rem 0;
	}

	.watch-link {
		display: inline-block;
		color: #ff8c42;
		text-decoration: none;
		font-size: 0.95rem;
		margin-top: 0.5rem;
	}

	.watch-link:hover {
		color: #ffa500;
		text-decoration: underline;
	}

	@media (max-width: 768px) {
		.result-card {
			flex-direction: column;
			gap: 1rem;
		}

		.result-number {
			font-size: 1.5rem;
			min-width: auto;
			text-align: left;
		}

		.title {
			font-size: 1.1rem;
		}

		.meta {
			font-size: 0.85rem;
		}

		.snippet {
			font-size: 0.95rem;
		}
	}
</style>