import 'dotenv/config';
import pg from 'pg';
if (!process.env.DATABASE_URL) throw new Error('DATABASE_URL não configurada. Copie .env.example para .env.');
export const pool = new pg.Pool({
  connectionString:process.env.DATABASE_URL,
  max:10,
  ...(process.env.PGSSL === 'true' ? {ssl:{rejectUnauthorized:true}} : {})
});
export async function transaction(fn){
  const c=await pool.connect();
  try { await c.query('BEGIN'); const result=await fn(c); await c.query('COMMIT'); return result; }
  catch(e){await c.query('ROLLBACK');throw e;} finally {c.release();}
}
export function fail(status,message){const e=new Error(message);e.status=status;return e;}
export async function queryRows(sql,args=[]){return (await pool.query(sql,args)).rows;}
