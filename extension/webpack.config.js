const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const webpack = require('webpack');
const dotenv = require('dotenv');
const fs = require('fs');

module.exports = (env, argv) => {
  const envFile = argv.mode === 'production' ? '../.env.prod' : '../.env';
  const envConfig = dotenv.config({ path: path.resolve(__dirname, envFile) });

  if (envConfig.error) {
    console.warn(`Warning: Could not load ${envFile}`);
  }

  const API_URL = process.env.PUBLIC_API_URL || 'http://localhost:8000';

  return {
    mode: argv.mode || 'development',
    devtool: false, // Disable source maps that use eval
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
              const manifest = JSON.parse(content.toString());

              // Apply production patches if building for production
              if (argv.mode === 'production') {
                const patchPath = path.resolve(__dirname, 'manifest.prod.patch.json');
                if (fs.existsSync(patchPath)) {
                  const patch = JSON.parse(fs.readFileSync(patchPath, 'utf8'));
                  Object.assign(manifest, patch);
                }
              }

              return JSON.stringify(manifest, null, 2);
            }
          },
          { from: 'popup/popup.html', to: 'popup/popup.html' },
          { from: 'popup/popup.css', to: 'popup/popup.css' },
          { from: 'icons', to: 'icons' }
        ]
      }),
      new webpack.DefinePlugin({
        'process.env.PUBLIC_API_URL': JSON.stringify(API_URL)
      })
    ]
  };
};