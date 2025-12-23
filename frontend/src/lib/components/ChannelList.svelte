<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import ProgressDisplay from './ProgressDisplay.svelte';

	const PUBLIC_API_URL = import.meta.env.PUBLIC_API_URL;
	export let channels: any[] = [];

	const dispatch = createEventDispatcher();

	let activeJobs: Record<string, { type: string; progress: any[] }> = {};
	let wsConnections: Record<string, WebSocket> = {};

	async function startJob(channelId: string, operation: 'check-new' | 'retry-failed') {
		try {
			const endpoint =
				operation === 'check-new'
					? `/api/channels/${channelId}/check-new-async`
					: `/api/channels/${channelId}/retry-failed-async`;

			const response = await fetch(`${PUBLIC_API_URL}${endpoint}`, {
				method: 'POST'
			});

			if (!response.ok) throw new Error('Failed to start operation');

			const data = await response.json();
			const jobId = data.job_id;

			// Initialize job tracking
			activeJobs[channelId] = { type: operation, progress: [] };

			// Connect to WebSocket
			const wsUrl = `${PUBLIC_API_URL.replace('http', 'ws')}/ws/channel-job/${jobId}`;
			const ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (activeJobs[channelId]) {
          activeJobs[channelId].progress = [...activeJobs[channelId].progress, message];
        }

        // Close job on complete, error, or new_videos_found with count 0
        if (message.event === 'complete' || message.event === 'error') {
          setTimeout(() => {
            delete activeJobs[channelId];
            if (wsConnections[channelId]) {
              wsConnections[channelId].close();
              delete wsConnections[channelId];
            }
            dispatch('refresh');
            activeJobs = { ...activeJobs };
          }, 2000);
        } else if (message.event === 'new_videos_found' && message.data.count === 0) {
          // No new videos found, close immediately
          setTimeout(() => {
            delete activeJobs[channelId];
            if (wsConnections[channelId]) {
              wsConnections[channelId].close();
              delete wsConnections[channelId];
            }
            dispatch('refresh');
            activeJobs = { ...activeJobs };
          }, 2000);
        }

        // Force reactivity
        activeJobs = { ...activeJobs };
      };

			wsConnections[channelId] = ws;
		} catch (e) {
			console.error(e);
			alert('Failed to start operation');
		}
	}

	function handleCheckNew(channelId: string) {
		startJob(channelId, 'check-new');
	}

	function handleRetryFailed(channelId: string) {
		startJob(channelId, 'retry-failed');
	}

	function cancelJob(channelId: string) {
		if (wsConnections[channelId]) {
			wsConnections[channelId].close();
			delete wsConnections[channelId];
		}
		delete activeJobs[channelId];
		activeJobs = { ...activeJobs };
	}

	function formatDate(dateString: string | null): string {
		if (!dateString) return 'Never';
		const date = new Date(dateString);
		return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
	}
</script>

<div class="channel-list">
	{#if channels.length === 0}
		<div class="empty-state">No channels yet. Add one above to get started!</div>
	{:else}
		{#each channels as channel}
			<div class="channel-card">
				<div class="channel-header">
					<div class="channel-info">
						<h3>{channel.channel_name}</h3>
						<a href={channel.channel_url} target="_blank" class="channel-link">
							{channel.channel_url}
						</a>
					</div>
					<div class="channel-stats">
						<div class="stat">
							<span class="stat-label">Videos:</span>
							<span class="stat-value">{channel.video_count}</span>
						</div>
						<div class="stat">
							<span class="stat-label">Transcripts:</span>
							<span class="stat-value">{channel.transcript_count}</span>
						</div>
						<div class="stat">
							<span class="stat-label">Coverage:</span>
							<span class="stat-value">
								{channel.video_count > 0
									? Math.round((channel.transcript_count / channel.video_count) * 100)
									: 0}%
							</span>
						</div>
					</div>
				</div>

				{#if channel.description}
					<p class="channel-description">{channel.description.substring(0, 150)}...</p>
				{/if}

				<div class="channel-meta">
					<span>Last checked: {formatDate(channel.last_checked)}</span>
				</div>

				{#if activeJobs[channel.channel_id]}
					<div class="job-progress">
						<div class="job-header">
							<strong>
								{activeJobs[channel.channel_id].type === 'check-new'
									? 'Checking for new videos...'
									: 'Retrying failed transcripts...'}
							</strong>
							<button on:click={() => cancelJob(channel.channel_id)} class="cancel-btn">
								Cancel
							</button>
						</div>
						<ProgressDisplay progress={activeJobs[channel.channel_id].progress} />
					</div>
				{:else}
					<div class="channel-actions">
						<button on:click={() => handleCheckNew(channel.channel_id)} class="action-button">
							Check for New Videos
						</button>
						<div class="action-group">
							<button
								on:click={() => handleRetryFailed(channel.channel_id)}
								class="action-button secondary"
							>
								Retry Failed
							</button>
							<!-- Future: Add dropdown for "Refresh All" option -->
						</div>
					</div>
				{/if}
			</div>
		{/each}
	{/if}
</div>

<style>
	.channel-list {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.empty-state {
		text-align: center;
		padding: 3rem;
		color: #d4a574;
		font-size: 1.1rem;
	}

	.channel-card {
		background: #241610;
		border: 2px solid #8b4513;
		padding: 1.5rem;
		transition: border-color 0.2s;
	}

	.channel-card:hover {
		border-color: #ff8c42;
	}

	.channel-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1rem;
		gap: 2rem;
	}

	.channel-info {
		flex: 1;
	}

	h3 {
		font-size: 1.5rem;
		color: #ffa500;
		margin: 0 0 0.5rem 0;
	}

	.channel-link {
		color: #d4a574;
		text-decoration: none;
		font-size: 0.9rem;
		word-break: break-all;
	}

	.channel-link:hover {
		color: #ff8c42;
	}

	.channel-stats {
		display: flex;
		gap: 1.5rem;
	}

	.stat {
		text-align: center;
	}

	.stat-label {
		display: block;
		font-size: 0.8rem;
		color: #8b7355;
		margin-bottom: 0.25rem;
	}

	.stat-value {
		display: block;
		font-size: 1.5rem;
		color: #ff8c42;
		font-weight: bold;
	}

	.channel-description {
		color: #d4a574;
		margin: 1rem 0;
		line-height: 1.5;
	}

	.channel-meta {
		color: #8b7355;
		font-size: 0.85rem;
		margin: 1rem 0;
	}

	.channel-actions {
		display: flex;
		gap: 1rem;
		margin-top: 1rem;
	}

	.action-group {
		display: flex;
		gap: 0.5rem;
	}

	.action-button {
		padding: 0.75rem 1.5rem;
		font-size: 0.95rem;
		font-family: 'Courier New', monospace;
		font-weight: bold;
		background: #ff8c42;
		color: #1a0f08;
		border: 2px solid #ff8c42;
		cursor: pointer;
		transition: all 0.2s;
	}

	.action-button:hover {
		background: #ffa500;
		border-color: #ffa500;
	}

	.action-button.secondary {
		background: #8b4513;
		color: #f4e4d4;
		border-color: #8b4513;
	}

	.action-button.secondary:hover {
		background: #a0522d;
		border-color: #a0522d;
	}

	.job-progress {
		margin-top: 1rem;
		padding: 1rem;
		background: #1a0f08;
		border: 2px solid #ff8c42;
	}

	.job-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
		color: #ffa500;
	}

	.cancel-btn {
		padding: 0.5rem 1rem;
		font-size: 0.85rem;
		font-family: 'Courier New', monospace;
		background: #8b0000;
		color: #fff;
		border: 2px solid #8b0000;
		cursor: pointer;
	}

	.cancel-btn:hover {
		background: #a00000;
		border-color: #a00000;
	}
</style>