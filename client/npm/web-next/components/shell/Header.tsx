'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Sun, Moon } from 'lucide-react';
import clsx from 'clsx';

const TABS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/search', label: 'Search' },
  { href: '/runs', label: 'Runs' },
  { href: '/storage', label: 'Storage' },
  { href: '/sources', label: 'Sources' },
];

export function Header() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();

  return (
    <header className="flex h-[52px] items-center justify-between gap-4 border-b border-border bg-bg-secondary px-5">
      <div className="flex flex-shrink-0 items-center gap-2">
        <div className="flex h-[26px] w-[26px] items-center justify-center rounded-[7px] bg-accent-primary text-[15px] font-extrabold text-white">
          ⬡
        </div>
        <div className="font-display text-[15px] font-bold tracking-tight text-text-primary">
          LO<span className="text-accent-primary">SE</span>ME
        </div>
      </div>

      <nav className="flex flex-1 justify-center gap-0.5">
        {TABS.map((tab) => {
          const active = pathname?.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={clsx(
                'rounded-md px-4 py-1.5 text-[13px] font-semibold transition-colors',
                active
                  ? 'bg-accent-primary/10 text-accent-primary'
                  : 'text-text-tertiary hover:bg-bg-hover hover:text-text-primary',
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-shrink-0 items-center gap-2">
        <button
          aria-label="Toggle theme"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="flex h-8 w-8 items-center justify-center rounded-[7px] border border-border text-text-secondary transition-colors hover:bg-bg-hover"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  );
}
