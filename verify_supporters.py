import asyncio
import aiohttp
import json
import os

SUPPORTERS_URL = "https://raw.githubusercontent.com/AlbertCohenhgs/public_lists/refs/heads/main/apoiadores.json"
LOCAL_FILE = "app/apoio/apoiadores.json"

async def check_supporters(registration):
    supporters = []
    print(f"Checking registration: {registration}")

    # 1. Try Online
    try:
        print(f"Fetching from {SUPPORTERS_URL}...")
        async with aiohttp.ClientSession() as session:
            async with session.get(SUPPORTERS_URL) as resp:
                if resp.status == 200:
                    supporters = await resp.json(content_type=None)
                    print(f"Online fetch success. Count: {len(supporters)}")
                    print(f"Sample data: {supporters[:2]}")
                else:
                    print(f"Online fetch failed with status: {resp.status}")
                    raise Exception("Status not 200")
    except Exception as e:
        print(f"Error fetching online: {e}")
        # 2. Fallback
        try:
            print(f"Reading from local file {LOCAL_FILE}...")
            with open(LOCAL_FILE, 'r') as f:
                supporters = json.load(f)
                print(f"Local read success. Count: {len(supporters)}")
        except Exception as local_e:
            print(f"Local read failed: {local_e}")

    is_supporter = False
    if registration and str(registration) in [str(s) for s in supporters]:
        is_supporter = True

    print(f"Is supporter? {is_supporter}")
    return is_supporter

async def main():
    print("--- Test 1: Valid registration ---")
    await check_supporters("2023307343")

    print("\n--- Test 2: Invalid registration ---")
    await check_supporters("0000000000")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
