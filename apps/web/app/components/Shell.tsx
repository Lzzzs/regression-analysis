'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/', label: '提交任务', icon: '📝' },
  { href: '/jobs', label: '任务列表', icon: '📋' },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* ── 侧边栏（md+）── */}
      <aside className="hidden md:flex md:w-52 flex-col bg-white border-r border-gray-100 fixed inset-y-0 left-0 z-10">
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-5 border-b border-gray-100">
          <div className="w-6 h-6 bg-gray-900 rounded-md flex-shrink-0" />
          <span className="text-sm font-bold text-gray-900">Portfolio Lab</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-0.5">
          {NAV.map(({ href, label, icon }) => (
            <Link
              key={href}
              href={href}
              className={[
                'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive(href)
                  ? 'bg-gray-100 text-gray-900 font-semibold'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
              ].join(' ')}
            >
              <span className="text-base">{icon}</span>
              {label}
            </Link>
          ))}
        </nav>

        {/* API 状态 */}
        <div className="px-4 py-3 border-t border-gray-100">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-xs text-gray-400">API 就绪</span>
          </div>
        </div>
      </aside>

      {/* ── 主内容区 ── */}
      <main className="flex-1 md:ml-52 pb-16 md:pb-0">
        {children}
      </main>

      {/* ── 底部 Tab 栏（< md）── */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-100 z-10 grid grid-cols-2">
        {NAV.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={[
              'flex flex-col items-center justify-center py-2 text-xs gap-0.5 transition-colors',
              isActive(href)
                ? 'text-gray-900 font-semibold'
                : 'text-gray-400',
            ].join(' ')}
          >
            <span className="text-lg leading-none">{icon}</span>
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
