declare module '*.css';
declare module 'react' {
  export function useState<T>(initial: T): [T, (value: T) => void];
  const React: { StrictMode: unknown };
  export default React;
}
declare module 'react-dom/client' { export function createRoot(element: Element): { render(node: unknown): void }; }
declare module 'react/jsx-runtime' { export const jsx: unknown; export const jsxs: unknown; export const Fragment: unknown; }
declare namespace JSX { interface IntrinsicElements { [elemName: string]: any } }
interface ImportMetaEnv { readonly VITE_API_URL?: string }
interface ImportMeta { readonly env: ImportMetaEnv }
