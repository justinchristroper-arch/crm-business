export const STAGES = ['Baru', 'Kualifikasi', 'Proposal', 'Negosiasi', 'Berhasil', 'Gagal'];
export const KEY = 'crm-business-v1';
export const money = value => new Intl.NumberFormat('id-ID', {style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value);
export const compactMoney = value => value >= 1e9 ? `Rp ${(value/1e9).toLocaleString('id-ID',{maximumFractionDigits:1})} M` : value >= 1e6 ? `Rp ${(value/1e6).toLocaleString('id-ID',{maximumFractionDigits:1})} jt` : money(value);
export function dateKey(date = new Date()) { return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`; }
export function offsetDate(days) { const d = new Date(); d.setDate(d.getDate()+days); return dateKey(d); }
export function seed() {
  return {
    version:1, workspace:'Nusantara Studio',
    contacts:[
      {id:'c1',name:'Dimas Pratama',company:'Aksara Digital',email:'dimas@example.com',phone:'0812 0000 1001',role:'Marketing Director'},
      {id:'c2',name:'Sarah Wijaya',company:'Bloom & Co.',email:'sarah@example.com',phone:'0812 0000 1002',role:'Founder'},
      {id:'c3',name:'Rizky Ananda',company:'Kopi Senja',email:'rizky@example.com',phone:'0812 0000 1003',role:'Business Owner'},
      {id:'c4',name:'Nadia Putri',company:'Forma Living',email:'nadia@example.com',phone:'0812 0000 1004',role:'Brand Manager'},
      {id:'c5',name:'Arif Setiawan',company:'Ventura Tech',email:'arif@example.com',phone:'0812 0000 1005',role:'Product Lead'},
      {id:'c6',name:'Michelle Tan',company:'Studio Rupa',email:'michelle@example.com',phone:'0812 0000 1006',role:'Creative Director'},
      {id:'c7',name:'Bima Saputra',company:'Langkah Travel',email:'bima@example.com',phone:'0812 0000 1007',role:'Founder'}
    ],
    leads:[
      {id:'l1',name:'Putri Maharani',company:'Lumi Skincare',email:'putri@example.com',source:'Instagram',status:'Baru',notes:'Mencari website katalog produk.',created:offsetDate(-2)},
      {id:'l2',name:'Andi Nugroho',company:'Ruang Kerja',email:'andi@example.com',source:'Referral',status:'Dihubungi',notes:'Butuh landing page untuk coworking space.',created:offsetDate(-4)},
      {id:'l3',name:'Fajar Ramadhan',company:'Nusa Foods',email:'fajar@example.com',source:'Website',status:'Kualifikasi',notes:'Anggaran Rp15 juta, target rilis bulan depan.',created:offsetDate(-7)},
      {id:'l4',name:'Clara Dewi',company:'Atelier Clara',email:'clara@example.com',source:'LinkedIn',status:'Baru',notes:'Tertarik dengan portfolio studio.',created:offsetDate(-1)}
    ],
    deals:[
      {id:'d1',title:'Website company profile',contact:'c1',value:18000000,stage:'Proposal',due:offsetDate(12),created:offsetDate(-20),closed:'',notes:'Website 8 halaman dan CMS. Proposal sudah dikirim.'},
      {id:'d2',title:'E-commerce Bloom',contact:'c2',value:32000000,stage:'Negosiasi',due:offsetDate(8),created:offsetDate(-30),closed:'',notes:'Diskusi scope integrasi pembayaran.'},
      {id:'d3',title:'Landing page Kopi Senja',contact:'c3',value:8500000,stage:'Kualifikasi',due:offsetDate(18),created:offsetDate(-10),closed:'',notes:'Menunggu brief dan foto produk.'},
      {id:'d4',title:'Katalog interaktif Forma',contact:'c4',value:24000000,stage:'Proposal',due:offsetDate(14),created:offsetDate(-15),closed:'',notes:'Katalog furnitur dengan filter kategori.'},
      {id:'d5',title:'Dashboard internal',contact:'c5',value:45000000,stage:'Baru',due:offsetDate(30),created:offsetDate(-3),closed:'',notes:'Discovery meeting dijadwalkan minggu ini.'},
      {id:'d6',title:'Portfolio Studio Rupa',contact:'c6',value:12000000,stage:'Berhasil',due:offsetDate(-5),created:offsetDate(-40),closed:offsetDate(-5),notes:'Kontrak disetujui. Mulai tahap desain.'},
      {id:'d7',title:'Booking website travel',contact:'c7',value:28000000,stage:'Berhasil',due:offsetDate(-12),created:offsetDate(-50),closed:offsetDate(-12),notes:'Deal berhasil setelah presentasi prototype.'},
      {id:'d8',title:'Brand microsite',contact:'c1',value:10000000,stage:'Berhasil',due:offsetDate(-42),created:offsetDate(-70),closed:offsetDate(-42),notes:'Microsite kampanye produk.'},
      {id:'d9',title:'Website membership',contact:'c5',value:22000000,stage:'Gagal',due:offsetDate(-18),created:offsetDate(-55),closed:offsetDate(-18),notes:'Klien menunda proyek karena anggaran.'}
    ],
    tasks:[
      {id:'t1',title:'Follow-up proposal Aksara',contact:'c1',date:offsetDate(0),priority:'Tinggi',done:false},
      {id:'t2',title:'Meeting scope e-commerce',contact:'c2',date:offsetDate(0),priority:'Tinggi',done:false},
      {id:'t3',title:'Minta brief dan foto produk',contact:'c3',date:offsetDate(1),priority:'Sedang',done:false},
      {id:'t4',title:'Kirim revisi penawaran Forma',contact:'c4',date:offsetDate(-1),priority:'Sedang',done:false},
      {id:'t5',title:'Discovery call Ventura',contact:'c5',date:offsetDate(3),priority:'Rendah',done:false},
      {id:'t6',title:'Kirim kontrak Studio Rupa',contact:'c6',date:offsetDate(-5),priority:'Sedang',done:true}
    ],
    activities:[{id:'a1',text:'Deal Portfolio Studio Rupa berhasil',date:new Date().toISOString()},{id:'a2',text:'Proposal dikirim ke Aksara Digital',date:new Date().toISOString()},{id:'a3',text:'Lead baru dari Instagram: Lumi Skincare',date:new Date().toISOString()}]
  };
}
export function stats(data, days=30) {
  const start = offsetDate(-(days-1)); const today = dateKey();
  const closed = data.deals.filter(d => d.closed && d.closed >= start && d.closed <= today);
  const won = closed.filter(d=>d.stage==='Berhasil');
  const active = data.deals.filter(d=>!['Berhasil','Gagal'].includes(d.stage));
  return {won:won.reduce((s,d)=>s+d.value,0), wonCount:won.length, activeCount:active.length, pipeline:active.reduce((s,d)=>s+d.value,0),winRate:closed.length?Math.round(won.length/closed.length*100):0,closedCount:closed.length};
}
export function moveDeal(data, id, stage) {
  if(!STAGES.includes(stage)) return false;
  const deal=data.deals.find(d=>d.id===id); if(!deal) return false;
  deal.stage=stage; deal.closed=['Berhasil','Gagal'].includes(stage)?dateKey():''; return true;
}
export function validateBackup(data) {
  if(!data || data.version!==1 || typeof data.workspace!=='string' || !data.workspace.trim() || data.workspace.length>80) throw Error('Format backup tidak valid.');
  const collections=['contacts','leads','deals','tasks','activities'];
  const str=(r,k)=>typeof r[k]==='string' && r[k].length<=5000;
  const validDate=s=>/^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(s));
  for(const key of collections) {
    if(!Array.isArray(data[key]) || data[key].length>10000) throw Error('Koleksi backup tidak valid.');
    const ids=new Set();
    for(const r of data[key]) {
      if(!r || !str(r,'id') || !r.id || ids.has(r.id)) throw Error('ID backup tidak valid.'); ids.add(r.id);
      const fields={contacts:['name','company','email','phone','role'],leads:['name','company','email','source','status','notes','created'],deals:['title','contact','stage','due','created','closed','notes'],tasks:['title','contact','date','priority'],activities:['text','date']}[key];
      if(!fields.every(k=>str(r,k))) throw Error('Isi backup tidak valid.');
      if(key==='deals' && (!Number.isFinite(r.value)||r.value<0||!STAGES.includes(r.stage)||!validDate(r.due)||!validDate(r.created)||(r.closed&&!validDate(r.closed)))) throw Error('Deal backup tidak valid.');
      if(key==='tasks' && (typeof r.done!=='boolean'||!validDate(r.date)||!['Tinggi','Sedang','Rendah'].includes(r.priority))) throw Error('Tugas backup tidak valid.');
      if(key==='leads' && (!validDate(r.created)||!['Baru','Dihubungi','Kualifikasi','Dikonversi','Tidak cocok'].includes(r.status))) throw Error('Lead backup tidak valid.');
    }
  }
  const contacts=new Set(data.contacts.map(c=>c.id));
  if(data.deals.some(d=>!contacts.has(d.contact))||data.tasks.some(t=>t.contact&&!contacts.has(t.contact))) throw Error('Relasi kontak backup tidak valid.');
  return data;
}
