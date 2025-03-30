import asyncio
from main_bot import dp as main_dp
from admin_bot import dp_admin as admin_dp

async def start_main_bot():
    await main_dp.start_polling()

async def start_admin_bot():
    await admin_dp.start_polling()

async def main():
    await asyncio.gather(
        start_main_bot(),
        start_admin_bot()
    )

if __name__ == '__main__':
    asyncio.run(main())
