import {defineConfig} from '@playwright/test';
const python=process.platform==='win32'?'.venv\\Scripts\\python.exe':'python';
export default defineConfig({
  testDir:'./tests/e2e',fullyParallel:false,workers:1,timeout:45000,
  use:{baseURL:'http://127.0.0.1:8766',browserName:'chromium',trace:'off',screenshot:'only-on-failure'},
  webServer:{command:`"${python}" scripts/e2e_server.py`,url:'http://127.0.0.1:8766/api/health',reuseExistingServer:false,timeout:60000}
});
