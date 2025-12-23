import { browser } from '$app/environment';

export function getApiUrl(): string {
	return browser
		? import.meta.env.PUBLIC_API_URL
		: 'http://backend:8000';
}