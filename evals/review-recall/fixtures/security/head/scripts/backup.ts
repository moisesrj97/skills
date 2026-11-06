import { execSync } from 'node:child_process';

execSync(`mongodump --uri=${process.env.MONGO_URL} --out=/backups/${new Date().toISOString()}`);
