export type RepoStats = {
  stars: number;
  forks: number;
  release: { tag: string; url: string } | null;
};

const API = 'https://api.github.com/repos/juniorterin/fliperOS';
const HEADERS = { Accept: 'application/vnd.github+json', 'User-Agent': 'fliperos-website' };

async function getJson(url: string): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetch(url, {
      headers: HEADERS,
      signal: AbortSignal.timeout(4000),
      next: { revalidate: 3600 },
    });
    return res.ok ? ((await res.json()) as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

// API pública sem token (60 pedidos/hora por IP): se falhar, a seção mostra só o CTA.
export async function getRepoStats(): Promise<RepoStats | null> {
  const repo = await getJson(API);
  if (!repo || typeof repo.stargazers_count !== 'number' || typeof repo.forks_count !== 'number') return null;
  const latest = await getJson(`${API}/releases/latest`);
  const release =
    latest && typeof latest.tag_name === 'string' && typeof latest.html_url === 'string'
      ? { tag: latest.tag_name, url: latest.html_url }
      : null;
  return { stars: repo.stargazers_count, forks: repo.forks_count, release };
}
