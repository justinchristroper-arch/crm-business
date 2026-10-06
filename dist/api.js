let csrf = '';
export class ApiError extends Error {
  constructor(message, status){super(message);this.status=status;}
}
export function setCsrf(value){csrf=value||'';}
export async function request(path, {method='GET', body, signal}={}) {
  const headers = {'Accept':'application/json'};
  if(body!==undefined)headers['Content-Type']='application/json';
  if(!['GET','HEAD'].includes(method)&&csrf)headers['X-CSRF-Token']=csrf;
  let response;
  try {response=await fetch(`/api${path}`,{method,headers,credentials:'same-origin',body:body===undefined?undefined:JSON.stringify(body),signal:signal||AbortSignal.timeout(20000)});}
  catch(error){if(error.name==='AbortError'&&signal)throw error;throw new ApiError('Server tidak merespons. Muat ulang untuk memeriksa status perubahan sebelum mencoba lagi.',0);}
  const json=await response.json().catch(()=>({detail:'Respons server tidak valid.'}));
  if(!response.ok){const message=Array.isArray(json.detail)?json.detail.map(d=>`${d.loc?.slice(1).join('.')||'Data'}: ${d.msg}`).join('; '):json.detail;throw new ApiError(message||'Permintaan gagal.',response.status);}
  return json;
}
export const resource = kind => kind==='deals'?'opportunities':kind;
export const stageCode = value => ({Baru:'New',Kualifikasi:'Qualification',Proposal:'Proposal',Negosiasi:'Negotiation',Berhasil:'Won',Gagal:'Lost'}[value]||value);
export function recordPayload(kind, value){
  let result;
  if(kind==='contacts')result={name:value.name,company:value.company,email:value.email||'',phone:value.phone||'',role:value.role||''};
  if(kind==='companies')result={name:value.name};
  if(kind==='leads')result={name:value.name,company:value.company,email:value.email||'',source:value.source,status:value.status,notes:value.notes||''};
  if(kind==='deals')result={title:value.title,contact_id:value.contact||value.contact_id,value:String(value.value),stage:stageCode(value.stage),due:value.due,notes:value.notes||'',closing_reason:value.closing_reason||'',change_reason:value.change_reason||''};
  if(kind==='tasks')result={title:value.title,contact_id:value.contact||value.contact_id||null,lead_id:value.lead_id||null,opportunity_id:value.opportunity_id||null,date:value.date,priority:value.priority,done:!!value.done};
  if(value.owner_id)result.owner_id=value.owner_id;
  return result;
}
