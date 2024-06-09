#dev: @yummy1gay

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters.command import Command
from aiogram.enums import ParseMode
import asyncio
import logging
import requests
from config import *

logging.basicConfig(level=logging.INFO)

bot = Bot(token=bot_token)
dp = Dispatcher()
router = Router(name=__name__)

@router.message(Command("start"))
async def start(msg: Message):
    temp = await msg.answer("Загрузка данных...")
    wallet_url = f"https://tonapi.io/v2/accounts/{wallet}"
    events_url = f"https://tonapi.io/v2/accounts/{wallet}/events?limit={tx_quantity}"
    wallet_text = f"👛 <b>Ваш кошелек:</b> <code>{wallet}</code>\n\n"
    
    wallet_response = requests.get(wallet_url)
    
    if wallet_response.status_code == 200:
        wallet_data = wallet_response.json()
        balance_nano = wallet_data["balance"]
        balance_ton = balance_nano / 10**9
        balance_text = f"💳 <b>Баланс:</b> <code>{balance_ton:.8f}</code> <b>TON</b>\n\n"
    else:
        balance_text = "Ошибка при получении данных о балансе с API\n"
    
    events_response = requests.get(events_url)
    
    if events_response.status_code == 200:
        events_data = events_response.json()
        transactions_text = f"💸 <b>Последние {tx_quantity} транзакций:</b>\n"
        
        for event in events_data["events"]:
            if "TonTransfer" in event["actions"][0]:
                value = event["actions"][0]["simple_preview"]["value"]
                symbol = "➖" if event["actions"][0]["TonTransfer"]["sender"]["address"] == wallet_data["address"] else "➕"
            elif "JettonTransfer" in event["actions"][0]:
                description = event["actions"][0]["simple_preview"]["description"]
                value = ' '.join(description.split()[1:]) 
                symbol = "➖" if event["actions"][0]["JettonTransfer"]["sender"]["address"] == wallet_data["address"] else "➕"
            elif "NftItemTransfer" in event["actions"][0]:
                value = event["actions"][0]["simple_preview"]["value"]
                symbol = "➖" if event["actions"][0]["NftItemTransfer"]["sender"]["address"] == wallet_data["address"] else "➕"
            transaction_link = f"{symbol} <b><a href='https://tonscan.org/tx/{event['event_id']}'>{value}</a></b>\n"
            transactions_text += transaction_link
    else:
        transactions_text = "Ошибка при получении данных о транзакциях с API\n"

    await temp.edit_text(wallet_text + balance_text + transactions_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def check_transactions():
    last_event_id = None
    
    while True:
        events_url = f"https://tonapi.io/v2/accounts/{wallet}/events?limit=1"
        events_response = requests.get(events_url)
        
        if events_response.status_code == 200:
            events_data = events_response.json()
            new_event_id = events_data["events"][0]["event_id"]
            
            if last_event_id is None:
                last_event_id = new_event_id
            elif new_event_id != last_event_id:
                last_event_id = new_event_id
                
                wallet_url = f"https://tonapi.io/v2/accounts/{wallet}"
                wallet_response = requests.get(wallet_url)
                
                if wallet_response.status_code == 200:
                    wallet_data = wallet_response.json()
                    balance_nano = wallet_data["balance"]
                    balance_ton = balance_nano / 10**9
                    
                    await send_transaction_notification(events_data["events"][0], wallet_data, balance_ton)
            
        await asyncio.sleep(5)

async def send_transaction_notification(event, wallet_data, balance_ton):
    transaction_text = f"💸 <b>Новая транзакция:</b>\n"
    
    if "TonTransfer" in event["actions"][0]:
        value = event["actions"][0]["simple_preview"]["value"]
        symbol = "➖" if event["actions"][0]["TonTransfer"]["sender"]["address"] == wallet_data["address"] else "➕"
    elif "JettonTransfer" in event["actions"][0]:
        description = event["actions"][0]["simple_preview"]["description"]
        value = ' '.join(description.split()[1:]) 
        symbol = "➖" if event["actions"][0]["JettonTransfer"]["sender"]["address"] == wallet_data["address"] else "➕"
    elif "NftItemTransfer" in event["actions"][0]:
        value = event["actions"][0]["simple_preview"]["value"]
        symbol = "➖" if event["actions"][0]["NftItemTransfer"]["sender"]["address"] == wallet_data["address"] else "➕"
    
    transaction_link = f"{symbol} <b><a href='https://tonscan.org/tx/{event['event_id']}'>{value}</a></b>\n"
    balance_text = f"💳 <b>Баланс:</b> <code>{balance_ton:.8f}</code> <b>TON</b>\n\n"
    
    await bot.send_message(admin_id, transaction_text + transaction_link + balance_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def main():
    asyncio.create_task(check_transactions())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
