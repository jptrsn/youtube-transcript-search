import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';
import path from 'path';

export default defineConfig(({ mode }) => {
	// Load env from root directory
	const env = loadEnv(mode, path.resolve(__dirname, '..'), '');

	return {
		plugins: [sveltekit()],
		envDir: path.resolve(__dirname, '..'), // Look for .env files in root
		define: {
			'import.meta.env.PUBLIC_API_URL': JSON.stringify(env.PUBLIC_API_URL || 'http://localhost:8000'),
			'import.meta.env.PUBLIC_CHROME_EXTENSION_ID': JSON.stringify(env.PUBLIC_CHROME_EXTENSION_ID || '')
		}
	};
});