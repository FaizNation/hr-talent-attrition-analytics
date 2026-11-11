import { MongoClient } from 'mongodb';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/';
const DB_NAME = process.env.MONGO_DB_NAME || 'db_hr_mnc';

let client = null;
let db = null;

export async function connectDB() {
  if (db) return db;
  try {
    client = new MongoClient(MONGO_URI, {
      maxPoolSize: 50,
      serverSelectionTimeoutMS: 5000,
    });
    await client.connect();
    db = client.db(DB_NAME);
    console.log(`[MongoDB] Connected to database: ${DB_NAME}`);
    return db;
  } catch (err) {
    console.error('[MongoDB] Connection error:', err.message);
    throw err;
  }
}

export function getDB() {
  if (!db) {
    throw new Error('Database not initialized. Call connectDB first.');
  }
  return db;
}
