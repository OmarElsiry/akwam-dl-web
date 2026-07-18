import asyncio
import httpx

async def test():
    req = {
        "urls": [
            {
                "name": "Episode 7",
                "url": "https://akwam.com.co/episode/78412/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84-%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-7"
            }
        ]
    }
    
    # We will test the FastAPI endpoint directly by calling the function
    from api.index import bulk_resolve, BulkResolveRequest
    
    # Needs an event loop
    result = await bulk_resolve(BulkResolveRequest(**req))
    import json
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
