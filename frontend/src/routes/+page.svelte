<script lang="ts">
	import { onMount } from 'svelte';
	import { PUBLIC_API_URL } from '$env/static/public';
	import { goto } from '$app/navigation';

	let channels: any[] = [];
	let filteredChannels: any[] = [];
	let loading = true;
	let error = '';
	let searchQuery = '';

	$: {
		if (searchQuery.trim()) {
			const query = searchQuery.toLowerCase();
			filteredChannels = channels.filter(
				(c) =>
					c.channel_name.toLowerCase().includes(query) ||
					c.description?.toLowerCase().includes(query)
			);
		} else {
			filteredChannels = channels;
		}
	}

	async function loadChannels() {
		loading = true;
		error = '';

		try {
			const response = await fetch(`${PUBLIC_API_URL}/api/channels`);
			if (!response.ok) throw new Error('Failed to load channels');

			const data = await response.json();
			channels = data.channels;
		} catch (e) {
			error = 'Failed to load channels. Make sure the API is running.';
			console.error(e);
		} finally {
			loading = false;
		}
	}

	function handleChannelClick(channelId: string) {
		goto(`/channel/${channelId}`);
	}

	onMount(() => {
		loadChannels();
	});
</script>

<svelte:head>
	<title>YouTube Transcript Search</title>
</svelte:head>

<main>
	<div class="container">
		<header>
			<h1>YouTube Transcript Search</h1>
			<p class="tagline">Search transcripts across your favorite channels</p>
		</header>

		<div class="search-container">
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="Search channels..."
				class="channel-search"
			/>
		</div>

		{#if error}
			<div class="error">{error}</div>
		{/if}

		{#if loading}
			<div class="loading">Loading channels...</div>
		{:else}
			<div class="channels-grid">
				{#each filteredChannels as channel}
					<button class="channel-card" on:click={() => handleChannelClick(channel.channel_id)}>
						<h3>{channel.channel_name}</h3>
						{#if channel.description}
							<p class="description">{channel.description.substring(0, 150)}...</p>
						{/if}
						<div class="stats">
							<div class="stat">
								<span class="stat-value">{channel.video_count}</span>
								<span class="stat-label">videos</span>
							</div>
							<div class="stat">
								<span class="stat-value">{channel.transcript_count}</span>
								<span class="stat-label">transcripts</span>
							</div>
							<div class="stat">
								<span class="stat-value">
									{channel.video_count > 0
										? Math.round((channel.transcript_count / channel.video_count) * 100)
										: 0}%
								</span>
								<span class="stat-label">coverage</span>
							</div>
						</div>
					</button>
				{/each}
			</div>
		{/if}

		<div class="manage-link">
			<a href="/channels">Manage Channels →</a>
		</div>
	</div>
</main>

<style>

	main {
		padding: 2rem 1rem;
	}

	.container {
		max-width: 1200px;
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

	.search-container {
		margin-bottom: 2rem;
	}

	.channel-search {
		width: 100%;
		padding: 1rem 1.5rem;
		font-size: 1.1rem;
		font-family: 'Courier New', monospace;
		background: #1a0f08;
		color: #f4e4d4;
		border: 3px solid #ff8c42;
		outline: none;
		box-shadow: 8px 8px 0 #1a0f08;
	}

	.channel-search::placeholder {
		color: #8b7355;
	}

	.channel-search:focus {
		border-color: #ffa500;
		background: #241610;
	}

	.error {
		background: #8b0000;
		color: #fff;
		padding: 1rem;
		margin: 1rem 0;
		border: 2px solid #ff6b6b;
	}

	.loading {
		text-align: center;
		padding: 3rem;
		color: #d4a574;
		font-size: 1.2rem;
	}

	.channels-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1.5rem;
		margin-bottom: 3rem;
	}

	.channel-card {
		background: #1a0f08;
		border: 3px solid #8b4513;
		padding: 1.5rem;
		text-align: left;
		cursor: pointer;
		transition: all 0.2s;
		box-shadow: 6px 6px 0 #0f0805;
		width: 100%;
		font-family: 'Courier New', monospace;
	}

	.channel-card:hover {
		border-color: #ff8c42;
		transform: translate(-2px, -2px);
		box-shadow: 8px 8px 0 #0f0805;
	}

	h3 {
		color: #ffa500;
		margin: 0 0 1rem 0;
		font-size: 1.3rem;
	}

	.description {
		color: #d4a574;
		font-size: 0.9rem;
		line-height: 1.5;
		margin: 0 0 1rem 0;
	}

	.stats {
		display: flex;
		gap: 1rem;
		padding-top: 1rem;
		border-top: 2px solid #8b4513;
	}

	.stat {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.stat-value {
		font-size: 1.5rem;
		color: #ff8c42;
		font-weight: bold;
	}

	.stat-label {
		font-size: 0.75rem;
		color: #8b7355;
		text-transform: uppercase;
	}

	.manage-link {
		text-align: center;
		padding: 2rem 0;
	}

	.manage-link a {
		color: #d4a574;
		text-decoration: none;
		font-size: 1.1rem;
	}

	.manage-link a:hover {
		color: #ff8c42;
	}

	@media (max-width: 768px) {
		h1 {
			font-size: 2rem;
		}

		.channels-grid {
			grid-template-columns: 1fr;
		}
	}
</style>