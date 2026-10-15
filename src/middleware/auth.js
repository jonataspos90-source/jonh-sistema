import jwt from 'jsonwebtoken';
import {queryRows,fail} from '../db.js';
export function makeToken(user){
 return jwt.sign({sub:String(user.id),role:user.role},process.env.JWT_SECRET,{algorithm:'HS256',expiresIn:'8h',issuer:'john-sistemas'});
}
export async function requireAuth(req,res,next){
 try{
  const value=req.headers.authorization||'';
  if(!value.startsWith('Bearer '))throw fail(401,'Autenticação necessária.');
  const claims=jwt.verify(value.slice(7),process.env.JWT_SECRET,{algorithms:['HS256'],issuer:'john-sistemas'});
  const users=await queryRows('SELECT id,name,email,role FROM users WHERE id=$1 AND active=true',[claims.sub]);
  if(!users.length)throw fail(401,'Usuário inativo ou inexistente.');
  req.user=users[0];next();
 }catch(e){next(e.status?e:fail(401,'Sessão inválida ou expirada.'));}
}
export function permit(...roles){return (req,res,next)=>roles.includes(req.user.role)?next():next(fail(403,'Perfil sem permissão para esta operação.'));}
