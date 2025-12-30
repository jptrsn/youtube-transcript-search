# Build Instructions for YtScriBe

## Prerequisites

- Node.js 18+ and npm
- Operating System: macOS, Linux, or Windows
- zip utility (pre-installed on macOS/Linux, available on Windows via Git Bash or WSL)

## Environment Setup

1. Create environment file:
```bash
   cp .env.prod.example .env.prod
```

2. Edit `.env.prod` and set `PUBLIC_API_URL`:
```bash
   PUBLIC_API_URL=https://ytscri.be
```

   **Note**: The built extension will connect to this API endpoint. The production API
   at ytscri.be has CORS restrictions that only allow the officially published
   extension IDs. Reviewers building from source will be able to verify the build
   matches the submitted package, but will not be able to test functionality without
   configuring their own API instance.

## Build Steps

### For Firefox

1. Install dependencies:
```bash
   npm install
```

2. Build the Firefox production version:
```bash
   npm run build:firefox:prod
```

3. The packaged extension will be at `youtube-transcript-search-firefox.zip`

### For Chrome

1. Install dependencies:
```bash
   npm install
```

2. Build the Chrome production version:
```bash
   npm run build:chrome:prod
```

3. The packaged extension will be at `youtube-transcript-search-chrome.zip`

### For Edge

1. Install dependencies:
```bash
   npm install
```

2. Build the Edge production version:
```bash
   npm run build:edge:prod
```

3. The packaged extension will be at `youtube-transcript-search-edge.zip`

## What the Build Does

Each build command:
- Compiles TypeScript to JavaScript
- Bundles modules using Webpack
- Applies browser-specific manifest patches (from `manifest.{browser}.prod.patch.json`)
- Injects `PUBLIC_API_URL` from `.env.prod` via webpack DefinePlugin
- Copies static assets (HTML, CSS, icons) to `dist/`
- Creates a zip archive of the `dist/` directory

## Build Environment

- Node.js version: 18 or higher
- npm version: 9 or higher
- TypeScript: 5.9.3
- Webpack: 5.103.0
- cross-env: for cross-platform environment variables

## Build Output

The build process:
- Compiles TypeScript files from `src/` to JavaScript
- Bundles modules using Webpack (no minification or obfuscation)
- Applies browser-specific manifest patches
- Copies static assets to `dist/`
- Creates a zip archive named `youtube-transcript-search-{browser}.zip`

## Verification

To verify the build matches the submitted package:
1. Follow the appropriate build steps above
2. Extract and compare the generated `.zip` with the uploaded extension
3. All files should match exactly

## Testing Notes for Reviewers

The extension connects to an external API (ytscri.be) for transcript storage and search.
The production API uses CORS to restrict access to the officially published extension IDs.
Reviewers can verify the build process but will not be able to test API functionality
without setting up their own backend instance or temporarily modifying CORS settings.

The complete backend source code is available at: [your-github-repo-url]

## Browser-Specific Notes

- **Firefox**: Uses `background.scripts` instead of `background.service_worker`
- **Chrome/Edge**: Uses `background.service_worker` and includes extension public key for consistent ID
- All browsers use the same TypeScript source code with browser-specific manifest patches applied at build time