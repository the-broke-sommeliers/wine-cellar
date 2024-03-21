module.exports = {
  env: {
    browser: true,
    es2021: true
  },
  extends: 'standard',
  ignorePatterns: [
    'node_modules/',
    'venv/',
    'static/',
    'webpack.*'
  ],
  overrides: [
    {
      env: {
        node: true
      },
      files: [
        '.eslintrc.{js,cjs}'
      ],
      parserOptions: {
        sourceType: 'script'
      }
    }
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  rules: {
    'space-before-function-paren': ['error', 'never']
  }
}
