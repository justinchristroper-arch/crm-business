import {randomBytes} from 'node:crypto';
import {existsSync,writeFileSync} from 'node:fs';
if(existsSync('.env')) throw Error('Preserving existing .env; configure it manually.');
writeFileSync('.env', `DATABASE_URL=postgresql+psycopg://crm_local@127.0.0.1:55432/crm_business\nMIGRATION_DATABASE_URL=postgresql+psycopg://crm_local@127.0.0.1:55432/crm_business\nTEST_DATABASE_URL=postgresql+psycopg://crm_local@127.0.0.1:55432/crm_business_test\nJWT_SECRET=${randomBytes(48).toString('base64url')}\nAPP_ENV=development\nALLOWED_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000"]\nCOOKIE_SECURE=false\nDEMO_MODE=true\nENABLE_DEMO_RESET=true\nREPORT_TIMEZONE=Asia/Jakarta\n`);
console.log('Local .env created; secret value was not printed.');
