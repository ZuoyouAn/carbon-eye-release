import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: '左右视频站',
    short_name: '左右视频站',
    description: '影视搜索、直播与异地同步放映厅',
    start_url: '/',
    display: 'standalone',
    background_color: '#f6f7f9',
    theme_color: '#f6f7f9',
    icons: [
      {
        src: '/icons/icon-192.png',
        sizes: '192x192',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: '/icons/icon-512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any',
      },
    ],
  };
}
