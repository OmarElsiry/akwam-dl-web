import { NextResponse } from 'next/server';
import { akwamApi } from '@/lib/akwam';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const q = searchParams.get('q');
    const type = searchParams.get('type') as 'movie' | 'series' || 'movie';

    if (!q) {
        return NextResponse.json({ error: 'Query is required' }, { status: 400 });
    }

    try {
        const results = await akwamApi.search(q, type);

        // Return debug info if empty for troubleshooting on Vercel
        if (results.length === 0) {
            // We can't easily get the HTML here unless we modify akwamApi.search
            // For now, let's just return a placeholder so the UI can show something
            return NextResponse.json({
                results: [],
                debug: {
                    message: "No results. This might be due to bot protection or incorrect URL resolution.",
                    query: q,
                    type: type
                }
            });
        }

        return NextResponse.json(results);
    } catch (error: any) {
        console.error('Search error:', error);
        return NextResponse.json({ error: 'Failed to fetch search results', details: error.message }, { status: 500 });
    }
}
