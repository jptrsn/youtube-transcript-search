import { writable } from 'svelte/store';

export const extensionInstalled = writable<boolean>(false);
export const extensionChecked = writable<boolean>(false);