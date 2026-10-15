import {Router} from 'express';
import bcrypt from 'bcryptjs';
import {z} from 'zod';
import {pool,transaction,fail} from '../db.js';
import {makeToken,requireAuth,permit} from '../middleware/auth.js';
export const auth=Router();
const register=z.object({name:z.string().trim().min(2).max(120),email:z.string().email().max(180).transform(x=>x.toLowerCase()),password:z.string().min(10).max(128)});
const wrap=fn=>(req,res,next)=>Promise.resolve(fn(req,res,next)).catch(next);
function parse(schema,body){const out=schema.safeParse(body);if(!out.success)throw fail(422,out.error.issues.map(i=>`${i.path.join('.')}: ${i.message}`).join('; '));return out.data;}
auth.get('/status',wrap(async(req,res)=>{
 const {rows}=await pool.query('SELECT EXISTS(SELECT 1 FROM users) as initialized');res.json({initialized:rows[0].initialized});
}));
auth.post('/bootstrap',wrap(async(req,res)=>{
 const p=parse(register.extend({bootstrapSecret:z.string().min(16).max(256)}),req.body);
 if(!process.env.BOOTSTRAP_SECRET || p.bootstrapSecret!==process.env.BOOTSTRAP_SECRET) throw fail(403,'Chave de ativação inicial inválida.');
 const u=await transaction(async c=>{
  // Advisory lock impede duas configurações iniciais concorrentes.
  await c.query('SELECT pg_advisory_xact_lock(28492316)');
  if((await c.query('SELECT id FROM users LIMIT 1')).rowCount)throw fail(409,'Administrador já cadastrado.');
  return (await c.query('INSERT INTO users (name,email,password_hash,role) VALUES ($1,$2,$3,$4) RETURNING id,name,email,role',[p.name,p.email,await bcrypt.hash(p.password,12),'admin'])).rows[0];
 });
 res.status(201).json({user:u,token:makeToken(u)});
}));
auth.post('/login',wrap(async(req,res)=>{
 const p=parse(z.object({email:z.string().email().transform(x=>x.toLowerCase()),password:z.string().min(1)}),req.body);
 const {rows}=await pool.query('SELECT * FROM users WHERE email=$1 AND active=true',[p.email]);
 if(!rows.length||!(await bcrypt.compare(p.password,rows[0].password_hash)))throw fail(401,'E-mail ou senha inválidos.');
 const {id,name,email,role}=rows[0];res.json({user:{id,name,email,role},token:makeToken(rows[0])});
}));
auth.get('/me',requireAuth,(req,res)=>res.json(req.user));
auth.get('/users',requireAuth,permit('admin'),wrap(async(req,res)=>res.json((await pool.query('SELECT id,name,email,role,active,created_at FROM users ORDER BY name')).rows)));
auth.post('/users',requireAuth,permit('admin'),wrap(async(req,res)=>{
 const p=parse(register.extend({role:z.enum(['admin','operator','viewer'])}),req.body);
 try{
 const {rows}=await pool.query('INSERT INTO users (name,email,password_hash,role) VALUES ($1,$2,$3,$4) RETURNING id,name,email,role,active',[p.name,p.email,await bcrypt.hash(p.password,12),p.role]);res.status(201).json(rows[0]);
 }catch(e){if(e.code==='23505')throw fail(409,'E-mail já cadastrado.');throw e;}
}));
auth.patch('/users/:id',requireAuth,permit('admin'),wrap(async(req,res)=>{
 const p=parse(z.object({name:z.string().trim().min(2).max(120).optional(),role:z.enum(['admin','operator','viewer']).optional(),active:z.boolean().optional(),password:z.string().min(10).max(128).optional()}),req.body);
 if(!Object.keys(p).length)throw fail(422,'Nenhuma alteração enviada.');
 const existing=(await pool.query('SELECT * FROM users WHERE id=$1',[req.params.id])).rows[0];if(!existing)throw fail(404,'Usuário não encontrado.');
 if(String(req.user.id)===String(existing.id)&&(p.active===false||p.role&&p.role!=='admin'))throw fail(422,'Não é permitido retirar seu próprio acesso administrativo.');
 const {rows}=await pool.query('UPDATE users SET name=$2,role=$3,active=$4,password_hash=$5 WHERE id=$1 RETURNING id,name,email,role,active',[req.params.id,p.name??existing.name,p.role??existing.role,p.active??existing.active,p.password?await bcrypt.hash(p.password,12):existing.password_hash]);res.json(rows[0]);
}));
