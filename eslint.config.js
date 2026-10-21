import js from '@eslint/js';
import globals from 'globals';
export default [
  {ignores:['node_modules/**','artifacts/**','.venv/**','public/**']},
  js.configs.recommended,
  {files:['dist/**/*.js'],languageOptions:{globals:globals.browser},rules:{'no-unused-vars':['error',{caughtErrors:'none',argsIgnorePattern:'^_'}]}},
  {files:['tests/e2e/*.mjs'],languageOptions:{globals:{...globals.node,...globals.browser}}},
  {files:['*.mjs','scripts/*.mjs','tests/*.mjs','eslint.config.js'],languageOptions:{globals:globals.node}}
];
