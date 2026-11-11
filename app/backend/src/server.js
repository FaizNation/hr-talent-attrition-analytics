import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { connectDB } from './config/db.js';
import apiRouter from './routes/api.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({ path: path.resolve(__dirname, '../.env') });

const app = express();
const PORT = process.env.PORT || 5001;

app.use(cors({ origin: '*' }));
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', server_time: new Date().toISOString() });
});

// API routes
app.use('/api', apiRouter);

// Start server
async function start() {
  try {
    await connectDB();
    app.listen(PORT, () => {
      console.log(`[Express] HR Analytics Backend API listening on http://localhost:${PORT}`);
    });
  } catch (err) {
    console.error('Failed to start server:', err);
    process.exit(1);
  }
}

start();
