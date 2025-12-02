<script lang="ts">
	export let results: any[] = [];
	export let loading: boolean = false;
	export let snippets: Record<string, any> = {};
	export let loadingSnippets: boolean = false;
	export let searchQuery: string = ''; // NEW: Pass the query to determine if search was performed

	function formatTimestamp(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}
</script>

<div class="search-results">
	{#if !searchQuery}
		<!-- No search performed, show nothing -->
	{:else if loading}
		<div class="loading">Searching...</div>
	{:else if results.length === 0}
		<div class="no-results">No results found</div>
	{:else}
		<div class="results-header">
			<h2>Found {results.length} videos with matches</h2>
			{#if loadingSnippets}
				<span class="loading-snippets">Loading previews...</span>
			{/if}
		</div>

		<div class="results-list">
			{#each results as result}
				<div class="result-card">
					<div class="result-header">
						<a
							href="https://youtube.com/watch?v={result.video_id}"
							target="_blank"
							class="result-title"
						>
							{result.title}
						</a>
						<div class="match-badges">
							{#if result.transcript_matches > 0}
								<span class="badge badge-transcript">
									📝 {result.transcript_matches} transcript {result.transcript_matches === 1 ? 'match' : 'matches'}
								</span>
							{/if}
							{#if result.title_matches > 0}
								<span class="badge badge-title">🎬 title match</span>
							{/if}
							{#if result.description_matches > 0}
								<span class="badge badge-description">📄 description match</span>
							{/if}
						</div>
					</div>

					{#if snippets[result.video_id]}
						<div class="snippet-container">
							<div class="snippet">
								{@html snippets[result.video_id].snippet}
							</div>
							{#if snippets[result.video_id].timestamp}
							  <a
									href="https://youtube.com/watch?v={result.video_id}&t={Math.floor(snippets[result.video_id].timestamp)}s"
									target="_blank"
									class="timestamp-link"
								>
									⏱ {formatTimestamp(snippets[result.video_id].timestamp)}
								</a>
							{/if}
						</div>
					{:else if loadingSnippets}
						<div class="snippet-placeholder">
							<div class="shimmer"></div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.search-results {
		margin-top: 2rem;
	}

	.loading,
	.no-results {
		text-align: center;
		padding: 3rem;
		color: #d4a574;
		font-size: 1.2rem;
	}

	.results-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 3px solid #8b4513;
	}

	h2 {
		color: #ff8c42;
		font-size: 1.5rem;
		margin: 0;
	}

	.loading-snippets {
		color: #d4a574;
		font-size: 0.9rem;
		font-style: italic;
	}

	.results-list {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.result-card {
		background: #1a0f08;
		border: 3px solid #8b4513;
		padding: 1.5rem;
		transition: all 0.2s;
	}

	.result-card:hover {
		border-color: #ff8c42;
		transform: translate(-2px, -2px);
		box-shadow: 6px 6px 0 #0f0805;
	}

	.result-header {
		margin-bottom: 1rem;
	}

	.result-title {
		color: #ffa500;
		text-decoration: none;
		font-size: 1.3rem;
		font-weight: bold;
		display: block;
		margin-bottom: 0.75rem;
	}

	.result-title:hover {
		color: #ffb732;
		text-decoration: underline;
	}

	.match-badges {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.badge {
		padding: 0.25rem 0.75rem;
		border-radius: 3px;
		font-size: 0.85rem;
		font-weight: bold;
	}

	.badge-transcript {
		background: #2d5016;
		color: #90ee90;
	}

	.badge-title {
		background: #4a3520;
		color: #ffd700;
	}

	.badge-description {
		background: #3a3a52;
		color: #b0b0ff;
	}

	.snippet-container {
		margin-top: 1rem;
		padding: 1rem;
		background: #0f0805;
		border-left: 3px solid #ff8c42;
	}

	.snippet {
		color: #d4a574;
		line-height: 1.6;
		margin-bottom: 0.5rem;
	}

	.snippet :global(mark) {
		background: #ff8c42;
		color: #1a0f08;
		padding: 0.1rem 0.3rem;
		font-weight: bold;
	}

	.timestamp-link {
		color: #ff8c42;
		text-decoration: none;
		font-size: 0.9rem;
		display: inline-block;
		margin-top: 0.5rem;
	}

	.timestamp-link:hover {
		text-decoration: underline;
	}

	.snippet-placeholder {
		margin-top: 1rem;
		padding: 1rem;
		background: #0f0805;
		border-left: 3px solid #8b4513;
		height: 60px;
		position: relative;
		overflow: hidden;
	}

	.shimmer {
		width: 100%;
		height: 100%;
		background: linear-gradient(
			90deg,
			#0f0805 0%,
			#1a0f08 50%,
			#0f0805 100%
		);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite;
	}

	@keyframes shimmer {
		0% {
			background-position: -200% 0;
		}
		100% {
			background-position: 200% 0;
		}
	}

	@media (max-width: 768px) {
		.results-header {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.5rem;
		}

		.result-title {
			font-size: 1.1rem;
		}
	}
</style>