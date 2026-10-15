import {readFile} from 'node:fs/promises';
import {pool} from './db.js';
const sql=await readFile(new URL('../sql/001_initial.sql',import.meta.url),'utf8');
try {await pool.query(sql);console.log('Migração aplicada.');} finally {await pool.end();}
