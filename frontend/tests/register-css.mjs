import { readFileSync } from 'node:fs'
import { registerHooks } from 'node:module'

// Node does not compile CSS. Provide class exports for DOM behavior tests;
// Next's production build validates and scopes the actual stylesheets.
registerHooks({
  load(url, context, nextLoad) {
    if (!url.endsWith('.module.css')) return nextLoad(url, context)
    const css = readFileSync(new URL(url), 'utf8')
    const names = [...css.matchAll(/\.([a-zA-Z_][\w-]*)/g)].map((match) => match[1])
    const styles = Object.fromEntries(names.map((name) => [name, name]))
    return {
      format: 'module',
      source: `export default ${JSON.stringify(styles)}`,
      shortCircuit: true,
    }
  },
})
