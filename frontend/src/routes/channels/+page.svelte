<script lang="ts">
	import { onMount } from 'svelte';
	import ChannelList from '$lib/components/ChannelList.svelte';
	import AddChannelForm from '$lib/components/AddChannelForm.svelte';
	import { getApiUrl } from '$lib/utils/api';

	let channels: any[] = [];
	let loading = true;
	let error = '';

	async function loadChannels() {
		const API_URL = getApiUrl();
		loading = true;
		error = '';

		try {
			const response = await fetch(`${API_URL}/api/channels`);
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

	onMount(() => {
		loadChannels();
	});

	function handleChannelAdded() {
		loadChannels();
	}
</script>

<svelte:head>
	<title>Channels - YouTube Transcript Search</title>
</svelte:head>

<main>
	<div class="container">
		<header>
			<h1>Channel Management</h1>
			<a href="/" class="back-link">← Back to Search</a>
		</header>

		<section class="add-section">
			<h2>Add New Channel</h2>
			<AddChannelForm on:channelAdded={handleChannelAdded} />
		</section>

		<section class="channels-section">
			<h2>Your Channels</h2>
			{#if error}
				<div class="error">{error}</div>
			{/if}

			{#if loading}
				<div class="loading">Loading channels...</div>
			{:else}
				<ChannelList {channels} on:refresh={loadChannels} />
			{/if}
		</section>
	</div>
</main>

<style>
	main {
		padding: 2rem 1rem;
		min-height: 100vh;
	}

	.container {
		max-width: 1200px;
		margin: 0 auto;
	}

	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 3rem;
	}

	h1 {
		font-size: 2.5rem;
		margin: 0;
		color: #ff8c42;
		text-shadow: 3px 3px 0 #8b4513;
	}

	h2 {
		font-size: 1.5rem;
		color: #ffa500;
		margin-bottom: 1.5rem;
	}

	.back-link {
		color: #d4a574;
		text-decoration: none;
		font-size: 1.1rem;
	}

	.back-link:hover {
		color: #ff8c42;
	}

	.add-section,
	.channels-section {
		background: #1a0f08;
		border: 3px solid #8b4513;
		padding: 2rem;
		margin-bottom: 2rem;
		box-shadow: 6px 6px 0 #0f0805;
	}

	.error {
		background: #8b0000;
		color: #fff;
		padding: 1rem;
		border-radius: 4px;
		margin: 1rem 0;
		border: 2px solid #ff6b6b;
	}

	.loading {
		text-align: center;
		padding: 2rem;
		color: #d4a574;
	}

	@media (max-width: 768px) {
		header {
			flex-direction: column;
			align-items: flex-start;
			gap: 1rem;
		}

		h1 {
			font-size: 2rem;
		}

		h2 {
			font-size: 1.2rem;
		}

		.add-section,
		.channels-section {
			padding: 1rem;
		}

	}
</style>