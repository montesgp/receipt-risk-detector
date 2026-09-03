import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => ({
  plugins: [tailwindcss(), sveltekit()],
  // Vitest (mode: 'test') must resolve Svelte's client build, not the SSR
  // build, so `@testing-library/svelte`'s `mount()` works (see Svelte's
  // documented Vitest setup for component tests). Using the `mode` argument
  // (rather than `process.env`) avoids a dependency on Node type
  // definitions that are not installed in this workspace.
  resolve: mode === 'test' ? { conditions: ['browser'] } : undefined,
  test: {
    environment: 'jsdom',
    include: ['tests/unit/**/*.test.ts']
  }
}));
