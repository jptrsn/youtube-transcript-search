/* eslint-disable @typescript-eslint/no-explicit-any */
// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {

	interface Window {
		chrome?: typeof chrome;
		browser?: typeof browser;
	}

	// Chrome extension API types
	const chrome: {
		runtime: {
			sendMessage: (extensionId: string, message: any, callback: (response: any) => void) => void;
			lastError?: { message: string };
		};
	};

	// Firefox extension API types
	const browser: {
		runtime: {
			sendMessage: (extensionId: string, message: any) => Promise<any>;
			lastError?: { message: string };
		};
	};
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
