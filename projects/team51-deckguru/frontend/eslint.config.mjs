import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';
import pluginReactHooks from 'eslint-plugin-react-hooks';
import simpleImportSort from 'eslint-plugin-simple-import-sort';

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    '.next/**',
    'out/**',
    'build/**',
    'next-env.d.ts',
    'public/sw.js',
    'public/workbox-*.js',
  ]),
  {
    plugins: {
      'react-hooks': pluginReactHooks,
    },
    settings: { react: { version: 'detect' } },
    rules: {
      ...pluginReactHooks.configs['recommended-latest'].rules,
      // React scope는 새로운 JSX 변환에서는 필요하지 않음
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      // App Router를 사용하므로 이 규칙은 필요하지 않음
      '@next/next/no-html-link-for-pages': 'off',
    },
  },
  {
    plugins: {
      'simple-import-sort': simpleImportSort,
    },
    settings: {
      'import/resolver': {
        typescript: {
          alwaysTryTypes: true,
          project: 'tsconfig.json',
        },
        node: {
          extensions: ['.js', '.jsx', '.ts', '.tsx'],
        },
      },
    },
    rules: {
      // Import 관련 규칙들
      'import/no-unresolved': 'off',
      'import/no-duplicates': 'off',
      'import/no-unused-modules': 'warn',
      'import/newline-after-import': ['error', { count: 1 }],

      // Simple import sort (더 강력한 import 정렬)
      'simple-import-sort/imports': [
        'error',
        {
          groups: [
            ['^\\u0000.*'], // Side effects
            ['^(?=react)'], // React
            ['^(?=[@\\w])'], // External libraries
            ['^(?=\\.)'], // Relative imports
            ['.*\\.(png|webp|jpg|jpeg|svg|lottie|mp4|wav)$'], // Assets
          ],
        },
      ],

      // 사용하지 않는 변수 처리 (언더스코어로 시작하는 변수 무시)
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          varsIgnorePattern: '^_$',
          caughtErrorsIgnorePattern: '^_$',
        },
      ],

      // Type import 명시적 사용
      '@typescript-eslint/consistent-type-imports': [
        'error',
        {
          prefer: 'type-imports',
          fixStyle: 'inline-type-imports',
        },
      ],

      // 개행 규칙
      'padding-line-between-statements': [
        'error',
        { blankLine: 'always', prev: '*', next: '*' },
        { blankLine: 'any', prev: 'import', next: 'import' },
        { blankLine: 'any', prev: 'case', next: 'case' },
        { blankLine: 'any', prev: 'directive', next: 'directive' },
        { blankLine: 'any', prev: ['const', 'let'], next: ['const', 'let'] },
        { blankLine: 'any', prev: 'expression', next: 'expression' },
        { blankLine: 'any', prev: 'export', next: 'export' },
        { blankLine: 'any', prev: '*', next: 'break' },
      ],
    },
  },
]);

export default eslintConfig;
