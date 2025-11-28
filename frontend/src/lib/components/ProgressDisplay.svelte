<script lang="ts">
	export let progress: any[] = [];

	function getEventIcon(event: string): string {
		switch (event) {
			case 'status':
				return '🔍';
			case 'channel_id_extracted':
				return '✅';
			case 'channel_info':
				return '📺';
			case 'videos_found':
				return '📹';
			case 'video_progress':
				return '⏳';
			case 'video_status':
				return '📝';
			case 'complete':
				return '🎉';
			case 'error':
				return '❌';
			default:
				return '•';
		}
	}

	function formatMessage(message: any): string {
		const { event, data } = message;

		switch (event) {
			case 'status':
				return data.message;
			case 'channel_id_extracted':
				return `Channel ID: ${data.channel_id}`;
			case 'channel_info':
				return `Channel: ${data.channel_name}`;
			case 'videos_found':
				return `Found ${data.count} videos`;
			case 'video_progress':
				return `[${data.current}/${data.total}] ${data.title.substring(0, 50)}...`;
			case 'video_status':
				if (data.status === 'has_transcript') return 'Already has transcript';
				if (data.status === 'fetching_transcript') return 'Fetching transcript...';
				if (data.status === 'transcript_saved')
					return `Transcript saved (${data.length} chars)`;
				if (data.status === 'error') return `Error: ${data.error_type}`;
				return data.status;
			case 'complete':
				return `Complete! ${data.new_transcripts} new transcripts fetched`;
			case 'error':
				return `Error: ${data.message}`;
			default:
				return JSON.stringify(data);
		}
	}

	$: latestMessage = progress.length > 0 ? progress[progress.length - 1] : null;
	$: videoProgress = progress.find((p) => p.event === 'video_progress')?.data || null;
</script>

<div class="progress-display">
	<div class="current-status">
		{#if latestMessage}
			<span class="icon">{getEventIcon(latestMessage.event)}</span>
			<span class="message">{formatMessage(latestMessage)}</span>
		{/if}
	</div>

	{#if videoProgress}
		<div class="progress-bar">
			<div
				class="progress-fill"
				style="width: {(videoProgress.current / videoProgress.total) * 100}%"
			></div>
		</div>
		<div class="progress-text">{videoProgress.current} / {videoProgress.total} videos</div>
	{/if}

	<div class="log">
		{#each progress.slice(-10) as message}
			<div class="log-entry">
				<span class="log-icon">{getEventIcon(message.event)}</span>
				<span class="log-message">{formatMessage(message)}</span>
			</div>
		{/each}
	</div>
</div>

<style>
	.progress-display {
		width: 100%;
	}

	.current-status {
		font-size: 1.1rem;
		padding: 1rem;
		background: #241610;
		border: 2px solid #8b4513;
		margin-bottom: 1rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.icon {
		font-size: 1.5rem;
	}

	.message {
		color: #f4e4d4;
	}

	.progress-bar {
		height: 30px;
		background: #241610;
		border: 2px solid #8b4513;
		margin-bottom: 0.5rem;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, #ff8c42, #ffa500);
		transition: width 0.3s ease;
	}

	.progress-text {
		text-align: center;
		color: #d4a574;
		margin-bottom: 1rem;
		font-size: 0.9rem;
	}

	.log {
		max-height: 300px;
		overflow-y: auto;
		background: #0f0805;
		border: 2px solid #8b4513;
		padding: 1rem;
	}

	.log-entry {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
		font-size: 0.9rem;
		color: #d4a574;
	}

	.log-icon {
		flex-shrink: 0;
	}

	.log-message {
		word-break: break-word;
	}
</style>