import eslintConfigPrettier from 'eslint-config-prettier'
import neostandard from 'neostandard'

export default [
  ...neostandard({ts:true}),
  eslintConfigPrettier,
  {
    files: ['**/*.{js,mjs,cjs,jsx,mjsx,ts,tsx,mtsx,jest.jsx,jest.js}'],
    ignores: ['node_modules/', 'venv/', 'static/', 'wine_cellar/static/'],
  },
]
