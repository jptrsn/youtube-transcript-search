<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let channels: Array<{ name: string; count: number; enabled: boolean }> = [];

	const dispatch = createEventDispatcher();

	function toggleChannel(channelName: string) {
		const channel = channels.find((c) => c.name === channelName);
		if (!channel) return;

		dispatch('toggle', {
			channel: channelName,
			enabled: !channel.enabled
		});
	}

	function toggleAll(enable: boolean) {
		channels.forEach((channel) => {
			dispatch('toggle', {
				channel: channel.name,
				enabled: enable
			});
		});
	}

	$: allEnabled = channels.length > 0 && channels.every((c) => c.enabled);
	$: noneEnabled = channels.length > 0 && channels.every((c) => !c.enabled);
</script>

<div class="channel-filter">
	<div class="filter-header">
		<h3>Channels</h3>
		<div class="filter-actions">
			<button
				on:click={() => toggleAll(true)}
				disabled={allEnabled}
				class="action-btn"
				title="Select all"
			>
				All
			</button>
			<button
				on:click={() => toggleAll(false)}
				disabled={noneEnabled}
				class="action-btn"
				title="Deselect all"
			>
				None
			</button>
		</div>
	</div>

	<div class="channel-list">
		{#each channels as channel}
			<label class="channel-item" class:disabled={!channel.enabled}>
				<input
					type="checkbox"
					checked={channel.enabled}
					on:change={() => toggleChannel(channel.name)}
				/>
				<span class="channel-name">{channel.name}</span>
				<span class="channel-count">{channel.count}</span>
			</label>
		{/each}
	</div>
</div>

<style>
	.channel-filter {
		background: #1a0f08;
		border: 3px solid #8b4513;
		padding: 1.5rem;
		box-shadow: 6px 6px 0 #0f0805;
	}

	.filter-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
		padding-bottom: 0.75rem;
		border-bottom: 2px solid #8b4513;
	}

	h3 {
		margin: 0;
		color: #ff8c42;
		font-size: 1.2rem;
	}

	.filter-actions {
		display: flex;
		gap: 0.5rem;
	}

	.action-btn {
		padding: 0.25rem 0.75rem;
		font-size: 0.8rem;
		font-family: 'Courier New', monospace;
		background: #8b4513;
		color: #f4e4d4;
		border: 1px solid #8b4513;
		cursor: pointer;
		transition: all 0.2s;
	}

	.action-btn:hover:not(:disabled) {
		background: #a0522d;
		border-color: #a0522d;
	}

	.action-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.channel-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.channel-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem;
		cursor: pointer;
		transition: background 0.2s;
		border: 1px solid transparent;
	}

	.channel-item:hover {
		background: #241610;
		border-color: #8b4513;
	}

	.channel-item.disabled {
		opacity: 0.5;
	}

	input[type='checkbox'] {
		width: 18px;
		height: 18px;
		cursor: pointer;
		accent-color: #ff8c42;
	}

	.channel-name {
		flex: 1;
		color: #f4e4d4;
		font-size: 0.95rem;
	}

	.channel-count {
		color: #d4a574;
		font-size: 0.85rem;
		background: #241610;
		padding: 0.25rem 0.5rem;
		border-radius: 10px;
		min-width: 2rem;
		text-align: center;
	}

  @media (max-width: 768px) {
		.channel-filter {
			padding: 1rem;
		}

		h3 {
			font-size: 1rem;
		}

		.channel-name {
			font-size: 0.9rem;
		}
	}
</style>