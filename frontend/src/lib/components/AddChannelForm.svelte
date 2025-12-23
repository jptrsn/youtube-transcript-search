<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import ProgressDisplay from './ProgressDisplay.svelte';

	const PUBLIC_API_URL = import.meta.env.PUBLIC_API_URL;
	const dispatch = createEventDispatcher();

	let channelUrl = '';
	let jobId: string | null = null;
	let wsConnection: WebSocket | null = null;
	let progress: any[] = [];
	let isRunning = false;
	let error = '';

	async function handleSubmit() {
		if (!channelUrl.trim()) return;

		error = '';
		isRunning = true;
		progress = [];

		try {
			// Start the job
			const response = await fetch(
				`${PUBLIC_API_URL}/api/channels/add-async?channel_url=${encodeURIComponent(channelUrl)}`
			, {
				method: 'POST'
			});

			if (!response.ok) throw new Error('Failed to start channel import');

			const data = await response.json();
			jobId = data.job_id;

			// Connect to WebSocket for progress updates
			const wsUrl = `${PUBLIC_API_URL.replace('http', 'ws')}/ws/channel-job/${jobId}`;
			wsConnection = new WebSocket(wsUrl);

			wsConnection.onmessage = (event) => {
				const message = JSON.parse(event.data);
				progress = [...progress, message];

				if (message.event === 'complete') {
					isRunning = false;
					dispatch('channelAdded');
					setTimeout(() => {
						channelUrl = '';
						progress = [];
						jobId = null;
					}, 3000);
				}

				if (message.event === 'error') {
					isRunning = false;
					error = message.data.message;
				}
			};

			wsConnection.onerror = () => {
				error = 'WebSocket connection failed';
				isRunning = false;
			};

			wsConnection.onclose = () => {
				if (isRunning) {
					error = 'Connection closed unexpectedly';
					isRunning = false;
				}
			};
		} catch (e) {
			error = String(e);
			isRunning = false;
		}
	}

	function handleCancel() {
		if (wsConnection) {
			wsConnection.close();
		}
		isRunning = false;
		progress = [];
		jobId = null;
	}
</script>

<div class="form-container">
	{#if !isRunning}
		<div class="input-group">
			<input
				type="text"
				bind:value={channelUrl}
				placeholder="https://youtube.com/@channelname"
				class="channel-input"
			/>
			<button on:click={handleSubmit} disabled={!channelUrl.trim()} class="submit-button">
				Add Channel
			</button>
		</div>
	{:else}
		<div class="progress-container">
			<ProgressDisplay {progress} />
			<button on:click={handleCancel} class="cancel-button">Cancel</button>
		</div>
	{/if}

	{#if error}
		<div class="error">{error}</div>
	{/if}
</div>

<style>
	.form-container {
		width: 100%;
	}

	.input-group {
		display: flex;
		gap: 1rem;
	}

	.channel-input {
		flex: 1;
		padding: 1rem;
		font-size: 1rem;
		font-family: 'Courier New', monospace;
		background: #241610;
		color: #f4e4d4;
		border: 2px solid #8b4513;
		outline: none;
	}

	.channel-input:focus {
		border-color: #ff8c42;
	}

	.submit-button,
	.cancel-button {
		padding: 1rem 2rem;
		font-size: 1rem;
		font-family: 'Courier New', monospace;
		font-weight: bold;
		border: 2px solid;
		cursor: pointer;
		transition: all 0.2s;
	}

	.submit-button {
		background: #ff8c42;
		color: #1a0f08;
		border-color: #ff8c42;
	}

	.submit-button:hover:not(:disabled) {
		background: #ffa500;
		border-color: #ffa500;
	}

	.submit-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.cancel-button {
		background: #8b0000;
		color: #fff;
		border-color: #8b0000;
		margin-top: 1rem;
	}

	.cancel-button:hover {
		background: #a00000;
		border-color: #a00000;
	}

	.progress-container {
		width: 100%;
	}

	.error {
		background: #8b0000;
		color: #fff;
		padding: 1rem;
		margin-top: 1rem;
		border: 2px solid #ff6b6b;
	}
</style>