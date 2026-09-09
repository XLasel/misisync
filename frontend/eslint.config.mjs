import { defineConfig, globalIgnores } from 'eslint/config'
import nextVitals from 'eslint-config-next/core-web-vitals'
import nextTypescript from 'eslint-config-next/typescript'

export default defineConfig([
  ...nextVitals,
  ...nextTypescript,
  globalIgnores(['.next/**', 'next-env.d.ts']),
  ...[
    ['shared', ['entities', 'features', 'widgets']],
    ['entities', ['features', 'widgets']],
    ['features', ['widgets']],
  ].map(([layer, forbidden]) => ({
    files: [`src/${layer}/**/*.{ts,tsx}`],
    rules: {
      'no-restricted-imports': [
        'error',
        { patterns: forbidden.flatMap((name) => [`@/${name}/**`, `**/${name}/**`]) },
      ],
    },
  })),
])
