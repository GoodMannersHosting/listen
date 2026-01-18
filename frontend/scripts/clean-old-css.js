#!/usr/bin/env node
import { readdir, unlink } from 'fs/promises';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const assetsDir = join(__dirname, '../../static/assets');

try {
  const files = await readdir(assetsDir);
  // Remove old hashed CSS files (main-[hash].css), but keep main.css
  const cssFiles = files.filter(file => file.match(/^main-[a-zA-Z0-9_-]+\.css$/));
  
  if (cssFiles.length > 0) {
    console.log(`Cleaning up ${cssFiles.length} old hashed CSS file(s)...`);
    for (const file of cssFiles) {
      const filePath = join(assetsDir, file);
      await unlink(filePath);
      console.log(`  Removed ${file}`);
    }
    console.log('Done!');
  } else {
    // No old files to clean up
    console.log('No old CSS files to clean up.');
  }
} catch (error) {
  if (error.code === 'ENOENT') {
    // Assets directory doesn't exist yet, that's fine
    console.log('Assets directory does not exist yet, skipping cleanup.');
  } else {
    console.error('Error cleaning up CSS files:', error);
    process.exit(1);
  }
}
