import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import path from 'path';
import fs from 'fs';

export default defineConfig(({ mode }) => {
	// Explicitly read the .env.prod or .env file
	const envFile = mode === 'production' ? '../.env.prod' : '../.env';
	const envPath = path.resolve(__dirname, envFile);

	console.log('Loading env from:', envPath);

	const env: Record<string, string> = {};
	if (fs.existsSync(envPath)) {
		const content = fs.readFileSync(envPath, 'utf-8');
		console.log('Raw file content:', content);
		console.log('Parsed env object:', env);
		content.split('\n').forEach(line => {
			const [key, ...valueParts] = line.split('=');
			if (key && valueParts.length) {
				env[key.trim()] = valueParts.join('=').trim();
			}
		});
	}

	console.log('PUBLIC_API_URL:', env.PUBLIC_API_URL);
	console.log('PUBLIC_CHROME_EXTENSION_ID:', env.PUBLIC_CHROME_EXTENSION_ID);

	return {
		plugins: [sveltekit()],
		define: {
			'import.meta.env.PUBLIC_API_URL': JSON.stringify(env.PUBLIC_API_URL || 'http://localhost:8000'),
			'import.meta.env.PUBLIC_CHROME_EXTENSION_ID': JSON.stringify(env.PUBLIC_CHROME_EXTENSION_ID || '')
		}
	};
});