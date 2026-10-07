'use client';

import { Activity, Code2, Cpu, Monitor, MonitorCog, Terminal, type LucideIcon } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';

const ICONS: LucideIcon[] = [Terminal, Cpu, Activity, MonitorCog, Monitor, Code2];
const COLORS = ['text-orange', 'text-purple', 'text-green', 'text-cyan', 'text-pink', 'text-yellow'];

export function BadgeBar() {
  const { t } = useI18n();
  return (
    <section aria-label={t.badges.label} className="relative border-y border-line/60 bg-bg-deeper/50">
      <ul className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-2.5 px-4 py-6 sm:gap-3 sm:px-6 lg:justify-between lg:px-8">
        {t.badges.items.map((label, i) => {
          const Icon = ICONS[i % ICONS.length];
          return (
            <li
              key={label}
              className="inline-flex items-center gap-2 rounded-full border border-line bg-bg/70 px-3.5 py-1.5 font-mono text-xs text-fg sm:text-sm"
            >
              <Icon className={`size-4 ${COLORS[i % COLORS.length]}`} aria-hidden="true" />
              {label}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
