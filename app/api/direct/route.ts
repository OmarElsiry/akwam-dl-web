import { NextResponse } from 'next/server';
import { akwamApi } from '@/lib/akwam';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const link = searchParams.get('link');

    if (!link) {
        return NextResponse.json({ error: 'Link is required' }, { status: 400 });
    }

    try {
        const directUrl = await akwamApi.getDirectUrl(link);
        return NextResponse.json({ directUrl });
    } catch (error) {
        console.error('Direct URL error:', error);
        return NextResponse.json({ error: 'Failed to fetch direct URL' }, { status: 500 });
    }
}
