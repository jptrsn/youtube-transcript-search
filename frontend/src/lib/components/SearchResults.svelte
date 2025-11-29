<script lang="ts">
	export let results: any[] = [];
	export let loading = false;

	interface Match {
		match_type: string;
		snippet: string;
		timestamp: number | null;
		rank: number;
	}

	interface GroupedVideo {
		video_id: string;
		title: string;
		channel_name: string;
		thumbnail_url: string;
		published_at: string;
		matches: Match[];
	}

	let expandedVideoId: string | null = null;

	// Group results by video
	$: groupedResults = results.reduce((acc: Record<string, GroupedVideo>, result: any) => {
		if (!acc[result.video_id]) {
			acc[result.video_id] = {
				video_id: result.video_id,
				title: result.title,
				channel_name: result.channel_name,
				thumbnail_url: result.thumbnail_url,
				published_at: result.published_at,
				matches: []
			};
		}
		acc[result.video_id].matches.push({
			match_type: result.match_type,
			snippet: result.snippet,
			timestamp: result.timestamp,
			rank: result.rank
		});
		return acc;
	}, {});

	$: videoResults = Object.values(groupedResults) as GroupedVideo[];

	function toggleExpanded(videoId: string) {
		if (expandedVideoId === videoId) {
			expandedVideoId = null;
		} else {
			expandedVideoId = videoId;
		}
	}

	function formatTimestamp(seconds: number | null): string {
		if (seconds === null) return '';
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	function getYouTubeUrl(videoId: string, timestamp: number | null): string {
		const baseUrl = `https://youtube.com/watch?v=${videoId}`;
		if (timestamp !== null) {
			const adjustedTimestamp = Math.max(0, Math.floor(timestamp) - 1);
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
	{:else if videoResults.length > 0}
		{#each videoResults as video, i}
			<article class="result-card">
				<div class="result-number">{i + 1}</div>
				<div class="result-content">
					<div class="video-header">
						<a href={getYouTubeUrl(video.video_id, video.matches[0].timestamp)} target="_blank" class="title">
							{video.title}
						</a>
						<div class="meta">
							<span class="channel">{video.channel_name}</span>
							<span class="separator">•</span>
							<span class="match-count">{video.matches.length} match{video.matches.length !== 1 ? 'es' : ''}</span>
						</div>
					</div>

					<!-- First match (always visible) -->
					<div class="match-item first-match">
						<div class="match-header">
							<span class="match-badge">{getMatchBadge(video.matches[0].match_type)}</span>
							{#if video.matches[0].timestamp !== null}
								<a
									href={getYouTubeUrl(video.video_id, video.matches[0].timestamp)}
									target="_blank"
									class="timestamp-link"
								>
									{formatTimestamp(video.matches[0].timestamp)}
								</a>
							{/if}
						</div>
						<p class="snippet">{video.matches[0].snippet}</p>
					</div>

					<!-- Additional matches (in accordion) -->
					{#if video.matches.length > 1}
						<button
							class="expand-button"
							on:click={() => toggleExpanded(video.video_id)}
							class:expanded={expandedVideoId === video.video_id}
						>
							{expandedVideoId === video.video_id ? '▼' : '▶'}
							Show {video.matches.length - 1} more match{video.matches.length - 1 !== 1 ? 'es' : ''}
						</button>

						{#if expandedVideoId === video.video_id}
							<div class="additional-matches">
								{#each video.matches.slice(1) as match}
									<div class="match-item">
										<div class="match-header">
											<span class="match-badge">{getMatchBadge(match.match_type)}</span>
											{#if match.timestamp !== null}
												<a
													href={getYouTubeUrl(video.video_id, match.timestamp)}
													target="_blank"
													class="timestamp-link"
												>
													{formatTimestamp(match.timestamp)}
												</a>
											{/if}
										</div>
										<p class="snippet">{match.snippet}</p>
									</div>
								{/each}
							</div>
						{/if}
					{/if}
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

	.video-header {
		margin-bottom: 1rem;
		padding-bottom: 1rem;
		border-bottom: 2px solid #8b4513;
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
	}

	.separator {
		margin: 0 0.5rem;
	}

	.channel {
		color: #ff8c42;
	}

	.match-count {
		color: #d4a574;
		font-weight: bold;
	}

	.match-item {
		background: #0f0805;
		padding: 1rem;
		border-left: 3px solid #ff8c42;
		margin-bottom: 0.5rem;
	}

	.first-match {
		margin-bottom: 1rem;
	}

	.match-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.match-badge {
		font-size: 0.85rem;
		color: #d4a574;
	}

	.timestamp-link {
		color: #ff8c42;
		text-decoration: none;
		font-size: 0.9rem;
		font-weight: bold;
	}

	.timestamp-link:hover {
		color: #ffa500;
		text-decoration: underline;
	}

	.snippet {
		color: #f4e4d4;
		line-height: 1.6;
		margin: 0;
	}

	.expand-button {
		width: 100%;
		padding: 0.75rem;
		margin: 0.5rem 0;
		background: #8b4513;
		color: #f4e4d4;
		border: 2px solid #8b4513;
		font-family: 'Courier New', monospace;
		font-size: 0.9rem;
		cursor: pointer;
		transition: all 0.2s;
		text-align: left;
	}

	.expand-button:hover {
		background: #a0522d;
		border-color: #a0522d;
	}

	.expand-button.expanded {
		background: #a0522d;
	}

	.additional-matches {
		margin-top: 0.5rem;
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