import { useEffect, useState, type FormEvent } from 'react';
import './account.css';
type User = { email: string; role: string; verified: boolean };
type Integration = { _id: string; provider: string; environment: string; status: string; masked: string };
type Session = { id: string; expires_at: string; current: boolean };
const base = '/api/v1/saas';
async function api(path: string, method = 'GET', body?: unknown): Promise<any> {
  const headers: Record<string, string> = {};
  if (method !== 'GET') {
    const r = await fetch(base+'/auth/csrf', { credentials: 'same-origin', cache: 'no-store' });
    if (!r.ok) throw new Error('Account service unavailable. Try again later.');
    headers['x-csrf-token'] = (await r.json()).csrf_token;
    headers['content-type'] = 'application/json'; headers['idempotency-key'] = crypto.randomUUID();
  }
  const r = await fetch(base+path, { method, headers, credentials: 'same-origin', cache: 'no-store',
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(5000) });
  if (!r.ok) {
    const messages: Record<number,string> = {400:'Check the form values. Passwords need 12–128 characters.',401:'Sign in again; credentials may be incorrect or your session expired.',403:'Operation not permitted. Verify your email before adding integrations.',404:'Record unavailable.',409:'Record exists or this change is not currently safe.',429:'Too many attempts. Wait one minute and try again.',503:'Account service unavailable. Try again later.'};
    throw new Error(messages[r.status] || 'Request could not be completed.');
  }
  return r.json();
}
type Submit = (event: FormEvent<HTMLFormElement>, path: string, success: string, method?: string, transform?: (form: FormData)=>unknown)=>void;
const password = (name: string, label: string, min=1) => <label>{label}<input name={name} type="password" required minLength={min} maxLength={512} autoComplete="off"/></label>;
export function Account() {
  const [open,setOpen] = useState(location.hash==='#account');
  const [user,setUser] = useState<User|null>(null);
  const [busy,setBusy] = useState(false), [message,setMessage] = useState(''), [error,setError] = useState('');
  const [register,setRegister] = useState(false), [rows,setRows] = useState<Integration[]>([]), [sessions,setSessions] = useState<Session[]>([]);
  const [replacement,setReplacement] = useState<string|null>(null);
  const [preferences,setPreferences] = useState({theme:'dark',timeframe:1});
  async function refresh() {
    try {
      setUser((await api('/auth/me')).user);
      const [a,b,c] = await Promise.all([api('/integrations'),api('/auth/sessions'),api('/settings')]);
      setRows(a.integrations);setSessions(b.sessions);setPreferences(c);
    } catch {setUser(null);setRows([]);setSessions([]);}
  }
  useEffect(()=>{const listener=()=>setOpen(location.hash==='#account');window.addEventListener('hashchange',listener);return()=>window.removeEventListener('hashchange',listener);},[]);
  useEffect(()=>{if(!open)return;void refresh();const timer=setInterval(()=>void refresh(),15000);return()=>clearInterval(timer);},[open]);
  async function action(work:()=>Promise<unknown>,success:string) {setBusy(true);setError('');setMessage('');try{await work();setMessage(success);await refresh();}catch(e){setError(e instanceof Error?e.message:'Request failed');}finally{setBusy(false);}}
  const submit:Submit=(event,path,success,method='POST',transform)=>{event.preventDefault();const form=event.currentTarget;const data=new FormData(form);void action(async()=>{await api(path,method,transform?transform(data):Object.fromEntries(data));form.reset();setReplacement(null);},success);};
  if(!open)return null;
  return <section className="account" aria-labelledby="account-heading"><div className="account-title"><h2 id="account-heading">Account & integrations</h2><a href="#workspace">Back to fixture workspace</a></div>
    <p>Local development only. No external email or exchange connection is made. Trading remains disabled.</p>
    {busy&&<p role="status">Working…</p>}{message&&<p role="status">{message}</p>}{error&&<p role="alert" className="form-error">{error}</p>}
    {!user?<div className="account-grid"><form onSubmit={e=>submit(e,'/auth/'+(register?'register':'login'),register?'Registration processed. Sign in to continue.':'Signed in')}><h3>{register?'Create account':'Sign in'}</h3><label>Email<input name="email" type="email" required maxLength={254} autoComplete="username"/></label>{password('password','Password',register?12:1)}<button disabled={busy}>{register?'Register':'Sign in'}</button><button type="button" onClick={()=>setRegister(!register)}>{register?'Use existing account':'Create account'}</button></form><Recovery submit={submit} busy={busy}/></div>:<>
      <p data-testid="signed-in">Signed in as {user.email} · {user.role==='PLATFORM_ADMIN'?'Platform administrator':'Tenant owner'} · {user.verified?'Email verified':'Email unverified'}</p>
      <button disabled={busy} onClick={()=>void action(()=>api('/auth/logout','POST'),'Signed out')}>Sign out</button><button disabled={busy} onClick={()=>void action(()=>api('/auth/logout-all','POST'),'All sessions revoked')}>Sign out everywhere</button>
      <div className="account-grid"><form onSubmit={e=>submit(e,'/settings','Preferences saved','PUT',()=>preferences)}><h3>Preferences</h3><label>Theme preference<select value={preferences.theme} onChange={e=>setPreferences({...preferences,theme:e.target.value})}><option value="dark">Dark</option><option value="system">System (saved for later)</option></select></label><label>Default timeframe preference<select value={preferences.timeframe} onChange={e=>setPreferences({...preferences,timeframe:Number(e.target.value)})}>{[1,5,15].map(n=><option key={n} value={n}>{n} minutes</option>)}</select></label><p>Preferences are saved privately; the fixture chart keeps its current selection.</p><button disabled={busy}>Save preferences</button></form>
      <form onSubmit={e=>submit(e,'/auth/password','Password changed. Sign in again.')}><h3>Change password</h3>{password('current_password','Current password')}{password('password','New password',12)}<button disabled={busy}>Change password</button></form><Recovery submit={submit} busy={busy}/></div>
      <h3>Active sessions</h3><ul>{sessions.map(s=><li key={s.id}>{s.current?'This session':'Other session'} · expires {new Date(s.expires_at).toLocaleString()} <button disabled={busy} onClick={()=>void action(()=>api('/auth/sessions/'+s.id,'DELETE'),'Session revoked')}>Revoke session</button></li>)}</ul>
      <h3>Settings &gt; Integrations</h3><p>API key and secret storage is for a future private-account connection. Public Binance market data needs no key or secret. Storing a credential does not connect the account or enable trading; connection remains unverified.</p>
      <form aria-label="Credential storage" onSubmit={e=>submit(e,'/integrations'+(replacement?'/'+replacement:''),'Stored — connection not verified',replacement?'PUT':'POST')}><h4>{replacement?'Replace stored credential':'Add credential'}</h4>{!replacement&&<><label>Provider<select name="provider">{user.role==='PLATFORM_ADMIN'?<><option>NEWS</option><option>MACRO</option></>:<option>BINANCE</option>}</select></label><label>Environment<select name="environment">{user.role==='PLATFORM_ADMIN'?<option>PLATFORM</option>:<><option>TESTNET</option><option>LIVE</option></>}</select></label></>}{password('api_key','API key')}{password('api_secret','API secret')}<button disabled={busy}>{replacement?'Save replacement':'Store credential'}</button>{replacement&&<button type="button" onClick={()=>setReplacement(null)}>Cancel replacement</button>}</form>
      <ul aria-label="Stored integrations">{rows.map(row=><li key={row._id}>{row.provider} / {row.environment} · {row.masked} · {row.status==='DISABLED'?'Disabled — connection not verified':'Stored — connection not verified'} <button onClick={()=>setReplacement(row._id)}>Replace</button><button disabled={busy} onClick={()=>void action(()=>api('/integrations/'+row._id+'/disable','POST'),'Credential disabled')}>Disable</button><button disabled={busy} onClick={()=>void action(()=>api('/integrations/'+row._id,'DELETE'),'Stored credential removed; no exchange-side action taken')}>Remove</button></li>)}</ul>
    </>}</section>;
}
function Recovery({submit,busy}:{submit:Submit;busy:boolean}) {
  const [purpose,setPurpose]=useState('verify');
  return <div><h3>Recovery & email verification</h3><p>Development delivery only. Read the encrypted local mailbox using the documented local tool. Tokens expire after 15 minutes.</p>
    <form onSubmit={e=>submit(e,'/auth/recovery/'+purpose,'If eligible, a local delivery was created. No external email was sent.')}><label>Recovery email<input type="email" name="email" required/></label><label>Purpose<select value={purpose} onChange={e=>setPurpose(e.target.value)}><option value="verify">Verify email</option><option value="reset">Reset password</option></select></label><button disabled={busy}>Request local delivery</button></form>
    <form onSubmit={e=>submit(e,'/auth/verify','Email verified')}>{password('token','Email verification token')}<button disabled={busy}>Verify email</button></form>
    <form onSubmit={e=>submit(e,'/auth/reset','Password reset. Sign in again.')}>{password('token','Password reset token')}{password('password','Reset password',12)}<button disabled={busy}>Reset password</button></form>
  </div>;
}
