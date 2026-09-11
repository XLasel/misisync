import type { MetadataRoute } from 'next'

import { site } from '@/shared/config/site'

export default function sitemap(): MetadataRoute.Sitemap {
  // Group selection lives on the home page; no fictional group URLs or modified dates.
  return [{ url: site.url, changeFrequency: 'weekly', priority: 1 }]
}
