import {test,expect} from '@playwright/test';

async function login(page,role){
  await page.goto('/');
  await page.getByRole('button',{name:role,exact:true}).click();
  await page.getByRole('button',{name:'Masuk ke workspace'}).click();
  await expect(page.getByRole('heading',{name:'Dashboard.',exact:true})).toBeVisible();
}

test('Sales lead details persist through conversion; Manager cannot silently rewrite Lost reason',async({page})=>{
  const name=`Browser regression ${Date.now()}`;
  await login(page,'Sales Rep');
  await page.locator('nav').getByRole('link',{name:'Leads',exact:true}).click();
  await page.getByRole('button',{name:'Tambah lead',exact:true}).first().click();
  const dialog=page.getByRole('dialog');
  await dialog.getByLabel('Nama lengkap').fill(name);
  await dialog.getByLabel('Perusahaan').fill(name+' Studio');
  await dialog.getByLabel('Email',{exact:true}).fill(`browser-${Date.now()}@example.com`);
  await dialog.getByLabel('Telepon').fill('081234567890');
  await dialog.getByLabel('Jabatan').fill('Procurement');
  await dialog.getByRole('button',{name:'Tambah lead',exact:true}).click();
  const row=page.getByRole('row').filter({hasText:name});
  await expect(row).toBeVisible();
  await row.getByRole('button',{name:'Konversi'}).click();
  await dialog.getByLabel('Nama peluang').fill(name+' Deal');
  await dialog.getByLabel('Nilai penawaran').fill('500000');
  await dialog.getByRole('button',{name:'Konversi lead'}).click();
  await expect(row).toContainText('Sudah dikonversi');
  await page.locator('nav').getByRole('link',{name:'Kontak',exact:true}).click();
  const contact=page.getByRole('row').filter({hasText:name});
  await expect(contact).toContainText('081234567890');
  await expect(contact).toContainText('Procurement');
  await page.locator('nav').getByRole('link',{name:'Pipeline',exact:true}).click();
  await page.getByRole('combobox',{name:'Tahap '+name+' Deal',exact:true}).selectOption({label:'Gagal'});
  await dialog.getByLabel('Alasan perubahan').fill('No budget');
  await dialog.getByRole('button',{name:'Simpan tahap'}).click();
  await expect(page.getByRole('combobox',{name:'Tahap '+name+' Deal',exact:true})).toHaveValue('Gagal');
  await page.reload();
  await expect(page.getByRole('combobox',{name:'Tahap '+name+' Deal',exact:true})).toHaveValue('Gagal');
  await page.getByRole('button',{name:'Keluar',exact:true}).click();
  await expect(page.getByRole('button',{name:'Manager',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Manager',exact:true}).click();
  await page.getByRole('button',{name:'Masuk ke workspace'}).click();
  await page.locator('nav').getByRole('link',{name:'Pipeline',exact:true}).click();
  await page.getByRole('button',{name:'Edit '+name+' Deal',exact:true}).click();
  await dialog.getByLabel('Alasan Gagal').fill('Corrected reason');
  await dialog.getByRole('button',{name:'Simpan perubahan'}).click();
  await expect(page.getByText('Manager/Admin harus mencatat alasan perubahan nilai atau tahap.',{exact:true})).toBeVisible();
  await dialog.getByLabel('Alasan perubahan (Manager/Admin)').fill('Customer correction reviewed');
  await dialog.getByRole('button',{name:'Simpan perubahan'}).click();
  await expect(dialog).not.toBeVisible();
  await page.locator('nav').getByRole('link',{name:'Laporan',exact:true}).click();
  await expect(page.getByRole('button').filter({hasText:'closing_reason_changed'}).first()).toBeVisible();
});

test('Mobile navigation and pagination remain usable',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await login(page,'Sales Rep');
  const tag='Pagination '+Date.now();
  const session=await (await page.request.get('/api/auth/me')).json();
  for(let i=0;i<55;i++){
    const response=await page.request.post('/api/leads',{headers:{'X-CSRF-Token':session.csrf,'Origin':'http://127.0.0.1:8766'},data:{name:`${tag} ${i}`,company:'Pagination Studio'}});
    expect(response.status()).toBe(201);
  }
  await page.getByRole('button',{name:'Buka navigasi',exact:true}).click();
  await page.locator('nav').getByRole('link',{name:'Leads',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Leads',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Berikutnya',exact:true})).toBeVisible();
  await page.getByRole('searchbox',{name:'Cari data'}).fill(tag);
  await expect(page.locator('.pagination-bar')).toContainText('dari 55');
  await page.getByRole('button',{name:'Berikutnya',exact:true}).click();
  await expect(page.locator('.pagination-bar')).toContainText('51–55');
  await expect(page.getByRole('button',{name:'Sebelumnya',exact:true})).toBeEnabled();
  await expect(page.getByRole('row').filter({hasText:tag})).toHaveCount(5);
  expect(await page.evaluate(()=>document.body.scrollWidth<=innerWidth)).toBeTruthy();
});
