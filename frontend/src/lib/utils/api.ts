import { browser } from '$app/environment';
import { dev } from '$app/environment';

export function getApiUrl(): string {
	if (browser) {
		// Client-side: use the public API URL
		return import.meta.env.PUBLIC_API_URL;
	} else {
		// Server-side: use internal Docker network in production, localhost in dev
		return dev ? 'http://localhost:8000' : 'http://backend:8000';
	}
}