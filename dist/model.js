export const STAGES = ['Baru', 'Kualifikasi', 'Proposal', 'Negosiasi', 'Berhasil', 'Gagal'];
export const money = value => new Intl.NumberFormat('id-ID', {style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value);
export const compactMoney = value => value >= 1e9 ? `Rp ${(value/1e9).toLocaleString('id-ID',{maximumFractionDigits:1})} M` : value >= 1e6 ? `Rp ${(value/1e6).toLocaleString('id-ID',{maximumFractionDigits:1})} jt` : money(value);
export function dateKey(date = new Date()) { return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`; }
export function offsetDate(days) { const d = new Date(); d.setDate(d.getDate()+days); return dateKey(d); }
