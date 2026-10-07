import { Reveal } from './Reveal';

type Props = {
  id: string;
  kicker: string;
  title: string;
  intro?: string;
  align?: 'left' | 'center';
};

export function SectionHeading({ id, kicker, title, intro, align = 'left' }: Props) {
  const centered = align === 'center';
  return (
    <Reveal className={centered ? 'mx-auto max-w-3xl text-center' : 'max-w-3xl'}>
      <p className="font-mono text-sm tracking-wide text-green">
        <span aria-hidden="true" className="text-comment">
          ${' '}
        </span>
        {kicker.toLowerCase()}
      </p>
      <h2 id={`${id}-title`} className="mt-3 text-3xl font-semibold tracking-tight text-balance text-fg sm:text-4xl lg:text-5xl">
        {title}
      </h2>
      {intro ? <p className="mt-5 text-lg leading-relaxed text-pretty text-muted">{intro}</p> : null}
    </Reveal>
  );
}
