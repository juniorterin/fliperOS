import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { ImageResponse } from 'next/og';

export const size = { width: 180, height: 180 };
export const contentType = 'image/png';

// O mesmo desenho do icon.svg, em PNG para iOS e o manifest.
export default function AppleIcon() {
  const svg = readFileSync(join(process.cwd(), 'src/app/icon.svg'));
  const src = `data:image/svg+xml;base64,${svg.toString('base64')}`;
  return new ImageResponse(
    (
      <div style={{ width: '100%', height: '100%', display: 'flex', background: '#21222c' }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} width={180} height={180} alt="" />
      </div>
    ),
    size,
  );
}
