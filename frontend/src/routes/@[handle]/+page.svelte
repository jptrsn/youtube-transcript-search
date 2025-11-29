<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

	let loading = true;
	let error = '';

	$: handle = $page.params.handle;

	async function resolveAndRedirect() {
		loading = true;
		error = '';

		try {
			const res = await fetch(`${API_URL}/api/channels/resolve-handle/${encodeURIComponent(handle as string)}`);

			if (!res.ok) {
				if (res.status === 404) {
					throw new Error('Channel not found');
				}
				throw new Error('Failed to resolve channel');
			}

			const data = await res.json();
			const channelId = data.channel_id;

			// Redirect to the channel page
			goto(`/channel/${channelId}`, { replaceState: true });
		} catch (err: any) {
			error = err.message;
			loading = false;
		}
	}

	onMount(() => {
		resolveAndRedirect();
	});
</script>

<div class="container">
	{#if loading}
		<div class="loading">Resolving channel...</div>
	{:else if error}
		<div class="error">{error}</div>
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
</style>