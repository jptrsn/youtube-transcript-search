const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const webpack = require('webpack');
const dotenv = require('dotenv');
const fs = require('fs');

module.exports = (env, argv) => {
  // Get build mode and target browser from environment
  const buildMode = process.env.BUILD_MODE || 'dev';
  const targetBrowser = process.env.TARGET_BROWSER || 'chrome';

  // Load appropriate .env file
  const envFile = buildMode === 'prod' ? '../.env.prod' : '../.env';
  const envConfig = dotenv.config({ path: path.resolve(__dirname, envFile) });

  if (envConfig.error) {
    console.warn(`Warning: Could not load ${envFile}`);
  }

  const API_URL = process.env.PUBLIC_API_URL || 'http://localhost:8000';

  console.log(`Building for: ${targetBrowser} (${buildMode})`);

  return {
    mode: buildMode === 'prod' ? 'production' : 'development',
    devtool: false,
    entry: {
      'background/service-worker': './src/background/service-worker.ts',
      'content/youtube': './src/content/youtube.ts',
      'popup/popup': './src/popup/popup.ts'
    },
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: '[name].js',
      clean: true
    },
    resolve: {
      extensions: ['.ts', '.js']
    },
    module: {
      rules: [
        {
          test: /\.ts$/,
          use: 'ts-loader',
          exclude: /node_modules/
        }
      ]
    },
    plugins: [
      new CopyPlugin({
        patterns: [
          {
            from: 'manifest.json',
            to: 'manifest.json',
            transform(content) {
              let manifest = JSON.parse(content.toString());

              // Apply browser + environment specific patch
              const patchFile = `manifest.${targetBrowser}.${buildMode}.patch.json`;
              const patchPath = path.resolve(__dirname, patchFile);

              if (fs.existsSync(patchPath)) {
                const patch = JSON.parse(fs.readFileSync(patchPath, 'utf8'));
                manifest = deepMerge(manifest, patch);
                console.log(`Applied ${patchFile}`);
              } else {
                console.warn(`Warning: ${patchFile} not found`);
              }

              return JSON.stringify(manifest, null, 2);
            }
          },
          { from: 'popup/popup.html', to: 'popup/popup.html' },
          { from: 'popup/popup.css', to: 'popup/popup.css' },
          { from: 'src/content/transcript-search.css', to: 'content/transcript-search.css' },
          { from: 'icons', to: 'icons' }
        ]
      }),
      new webpack.DefinePlugin({
        'process.env.PUBLIC_API_URL': JSON.stringify(API_URL)
      })
    ]
  };
};

// Deep merge utility function
function deepMerge(target, source) {
  const output = { ...target };

  for (const key in source) {
    if (Array.isArray(source[key])) {
      // Replace arrays entirely instead of merging
      output[key] = source[key];
    } else if (source[key] instanceof Object && key in target && !Array.isArray(target[key])) {
      output[key] = deepMerge(target[key], source[key]);
    } else {
      output[key] = source[key];
    }
  }

  return output;
}