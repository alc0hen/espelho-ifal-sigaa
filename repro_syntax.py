import asyncio

def sync_wrapper():
    async def async_inner():
        async for i in async_gen():
            yield i

    async def async_gen():
        yield 1

    # Validating syntax of async inside nested async function
    return async_inner

print("Syntax check passed")
