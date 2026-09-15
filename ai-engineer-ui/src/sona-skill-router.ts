export type SonaSkill = 'songwriter' | 'analyzer' | 'mastering' | 'trends' | 'production' | 'general'

export function detectSonaSkill(text: string): SonaSkill {
  const value = text.toLowerCase()
  if (/тренд|тренды|trend|актуаль|чарт|spotify|tiktok/.test(value)) return 'trends'
  if (/мастер|master|lufs|true peak|громк|потолок/.test(value)) return 'mastering'
  if (/анализ|analy|сведение|микс|bpm|тональ|вокал|динамик/.test(value)) return 'analyzer'
  if (/напис|текст|припев|куплет|hook|хук|рифм|песн|song/.test(value)) return 'songwriter'
  if (/продакшн|аранж|релиз|выпуск|production|release/.test(value)) return 'production'
  return 'general'
}

export const SONA_SKILLS = {
  songwriter: 'Songwriter: ideas, lyrics, hooks, structure, editing and prosody.',
  analyzer: 'Analyzer: audio measurements, timeline, intelligence, vocal and actionable mix notes.',
  mastering: 'Mastering: target LUFS, ceiling, intensity, profile, QC and downloadable result.',
  trends: 'Trends: verified market signals, inference, saturation, white space and current research.',
  production: 'Production: analyze → map music → direct song → master → verify.',
  general: 'General SØNA assistant: answer the user and choose a specialist skill when useful.',
} as const
