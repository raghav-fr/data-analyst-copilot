import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function formatNumber(num: number): string {
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
  return num.toLocaleString();
}

export function truncate(str: string, length: number): string {
  return str.length > length ? str.substring(0, length) + '...' : str;
}

export function getTypeColor(dtype: string): string {
  if (dtype.includes('int') || dtype.includes('float')) return 'text-blue-400';
  if (dtype.includes('object') || dtype.includes('string')) return 'text-emerald-400';
  if (dtype.includes('bool')) return 'text-purple-400';
  if (dtype.includes('datetime')) return 'text-amber-400';
  if (dtype.includes('category')) return 'text-pink-400';
  return 'text-slate-400';
}

export function getTypeIcon(dtype: string): string {
  if (dtype.includes('int') || dtype.includes('float')) return '#';
  if (dtype.includes('object') || dtype.includes('string')) return 'T';
  if (dtype.includes('bool')) return '?';
  if (dtype.includes('datetime')) return '📅';
  if (dtype.includes('category')) return '≡';
  return '·';
}

export function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    overview: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    statistics: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    visualization: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    cleaning: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    business: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    ml: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  };
  return colors[category] || 'bg-slate-500/20 text-slate-300 border-slate-500/30';
}
