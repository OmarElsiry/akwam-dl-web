import { NextResponse } from 'next/server';
import { akwamApi } from '@/lib/akwam';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const url = searchParams.get('url');

    if (!url) {
        return NextResponse.json({ error: 'URL is required' }, { status: 400 });
    }

    try {
        if (url.includes('/series/')) {
            const episodes = await akwamApi.fetchEpisodes(url);
            return NextResponse.json({ type: 'series', episodes });
        } else if (url.includes('/movie/') || url.includes('/episode/')) {
            const qualities = await akwamApi.getQualities(url);
            return NextResponse.json({ type: 'item', qualities });
        } else {
            return NextResponse.json({ error: 'Unsupported URL type' }, { status: 400 });
        }
    } catch (error) {
        console.error('Item fetch error:', error);
        return NextResponse.json({ error: 'Failed to fetch item details' }, { status: 500 });
    }
}
