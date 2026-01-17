import { MongoClient } from 'mongodb';

if (!process.env.MONGO_HOST) {
  throw new Error('Please add your Mongo connection string to .env.local');
}

const uri = process.env.MONGO_USER && process.env.MONGO_PASS
  ? `mongodb://${process.env.MONGO_USER}:${process.env.MONGO_PASS}@${process.env.MONGO_HOST}:${process.env.MONGO_PORT || 27017}/${process.env.MONGO_DB || 'chronos'}?authSource=admin`
  : `mongodb://${process.env.MONGO_HOST}:${process.env.MONGO_PORT || 27017}/${process.env.MONGO_DB || 'chronos'}`;

const options = {};

let client: MongoClient;
let clientPromise: Promise<MongoClient>;

if (process.env.NODE_ENV === 'development') {
  // In development mode, use a global variable so that the value
  // is preserved across module reloads caused by HMR (Hot Module Replacement).
  let globalWithMongo = global as typeof globalThis & {
    _mongoClientPromise?: Promise<MongoClient>;
  };

  if (!globalWithMongo._mongoClientPromise) {
    client = new MongoClient(uri, options);
    globalWithMongo._mongoClientPromise = client.connect();
  }
  clientPromise = globalWithMongo._mongoClientPromise;
} else {
  // In production mode, it's best to not use a global variable.
  client = new MongoClient(uri, options);
  clientPromise = client.connect();
}

export default clientPromise;

