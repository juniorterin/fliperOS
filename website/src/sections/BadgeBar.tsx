'use client';

import Image from 'next/image';
import { GithubIcon } from '@/components/GithubIcon';
import { useI18n } from '@/i18n/I18nProvider';

// O ícone de cada destaque, pelo id do item (badges.items no i18n):
// - "px:NOME": um ícone de pixel do próprio FliperOS (public/icons/pixel.svg,
//   gravado por tools/web-icons.py): o do Setup para o mesmo item, ou um
//   desenhado para esta faixa quando o Setup não tem;
// - um caminho: o ícone oficial do projeto ou da marca (public/icons, origem
//   no README de lá);
// - "github": a marca do GitHub, onde estão o código e as ISOs.
const ICONS: Record<string, string[]> = {
  ubuntu: ['/icons/ubuntu.svg'],
  kernel: ['/icons/linux.svg'],
  limine: ['/icons/limine.png'],
  khz: ['px:khz'],
  switchres: ['px:resolution'],
  crt: ['px:retest'],
  gpu: ['/icons/amd.svg', '/icons/nvidia.svg', '/icons/intel.svg'],
  vga: ['px:vga'],
  atom15: ['px:firmware'],
  groovymame: ['/icons/groovymame.png'],
  retroarch: ['/icons/retroarch.svg'],
  flycast: ['/icons/flycast.png'],
  supermodel: ['px:model3'],
  model2: ['/icons/model2.png'],
  pcsx2: ['/icons/pcsx2.png'],
  dolphin: ['/icons/dolphin.svg'],
  duckstation: ['/icons/duckstation.png'],
  hypseus: ['px:laserdisc'],
  openbor: ['/icons/openbor.png'],
  frontend: ['px:frontend'],
  'attract-mode': ['/icons/attract-mode.png'],
  'es-de': ['/icons/es-de.svg'],
  fightcade: ['/icons/fightcade.png'],
  link: ['px:globe'],
  netplay: ['px:netplay'],
  web: ['px:web'],
  obs: ['/icons/obs.svg'],
  osd: ['px:osd'],
  interlaced: ['px:mode480'],
  scanlines: ['px:scanlines'],
  colour: ['px:colour'],
  vertical: ['px:orientation'],
  multi: ['px:outputs'],
  latency: ['px:latency'],
  vulkan: ['px:vulkan'],
  guncon: ['px:guncon'],
  hotr: ['/icons/hotr.png'],
  ledspicer: ['px:ledbutton'],
  pixelcade: ['/icons/pixelcade.png'],
  zedmd: ['px:dmd'],
  romfilter: ['px:filter'],
  bios: ['px:chip'],
  scraper: ['px:scraper'],
  samba: ['px:services'],
  commercial: ['px:coin'],
  lab: ['px:lab'],
  ota: ['px:reset'],
  opensource: ['github'],
};

// Logotipos que são só o nome (o da Intel): na altura das letras, mais largos.
const WORDMARK: Record<string, number> = { '/icons/intel.svg': 30 };

function BadgeIcon({ icon }: { icon: string }) {
  if (icon === 'github') return <GithubIcon className="size-4 shrink-0 text-fg" />;
  if (icon.startsWith('px:')) {
    return (
      <svg className="size-4 shrink-0" aria-hidden="true" focusable="false">
        <use href={`/icons/pixel.svg#px-${icon.slice(3)}`} />
      </svg>
    );
  }
  const wordmark = WORDMARK[icon];
  return (
    <Image
      src={icon}
      alt=""
      aria-hidden="true"
      width={wordmark ?? 16}
      height={wordmark ? 12 : 16}
      unoptimized
      className={`${wordmark ? 'h-3' : 'h-4'} w-auto shrink-0 object-contain`}
    />
  );
}

export function BadgeBar() {
  const { t } = useI18n();
  return (
    <section aria-label={t.badges.label} className="relative border-y border-line/60 bg-bg-deeper/50">
      <ul className="flex w-full flex-wrap items-center justify-center gap-2.5 px-4 py-6 sm:gap-3 sm:px-6 lg:px-8 2xl:justify-between">
        {t.badges.items.map(({ id, label }) => (
          <li
            key={id}
            className="inline-flex items-center gap-2 rounded-full border border-line bg-bg/70 px-3.5 py-1.5 font-mono text-xs text-fg sm:text-sm"
          >
            <span className="inline-flex items-center gap-1">
              {(ICONS[id] ?? []).map((icon) => (
                <BadgeIcon key={icon} icon={icon} />
              ))}
            </span>
            {label}
          </li>
        ))}
      </ul>
    </section>
  );
}
