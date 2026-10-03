/**
 * Ambient module declarations for Next.js sub-paths.
 *
 * These are only needed when running `tsc --noEmit` directly (without the Next.js
 * language server plugin). In a real `next build`, these types come from
 * `next-env.d.ts` + the Next.js TypeScript plugin, so this file is harmless.
 */
declare module "next" {
  export type { Metadata, NextConfig } from "next/dist/types";
}
declare module "next/link" {
  import type { FC, AnchorHTMLAttributes } from "react";
  const Link: FC<
    AnchorHTMLAttributes<HTMLAnchorElement> & {
      href: string | { pathname?: string; query?: Record<string, string> };
      prefetch?: boolean;
      replace?: boolean;
      scroll?: boolean;
      shallow?: boolean;
    }
  >;
  export default Link;
}
declare module "next/dynamic" {
  import type { ComponentType } from "react";
  function dynamic<P>(
    loader: () => Promise<{ default: ComponentType<P> } | ComponentType<P>>,
    options?: {
      ssr?: boolean;
      loading?: ComponentType;
      suspense?: boolean;
    },
  ): ComponentType<P>;
  export default dynamic;
}
declare module "next/font/google" {
  interface FontModule {
    variable: string;
    style: { fontFamily: string };
    className: string;
  }
  export function IBM_Plex_Sans(options: {
    subsets?: string[];
    weight?: string[];
    variable?: string;
  }): FontModule;
  export function Inter(options: {
    subsets?: string[];
    variable?: string;
  }): FontModule;
}
declare module "next/navigation" {
  export function usePathname(): string;
  export function useRouter(): {
    push: (href: string) => void;
    replace: (href: string) => void;
    back: () => void;
  };
  export function useSearchParams(): URLSearchParams;
}
declare module "next/image" {
  import type { FC, ImgHTMLAttributes } from "react";
  const Image: FC<
    ImgHTMLAttributes<HTMLImageElement> & {
      src: string;
      alt: string;
      width?: number;
      height?: number;
      fill?: boolean;
      priority?: boolean;
    }
  >;
  export default Image;
}
