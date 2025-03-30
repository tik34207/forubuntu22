from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
import database as db

class BlockBannedMiddleware(BaseMiddleware):
    async def on_pre_process_update(self, update: types.Update, data: dict):
        user_id = None

        if update.message:
            user_id = update.message.from_user.id
        elif update.callback_query:
            user_id = update.callback_query.from_user.id

        if user_id:
            user = db.get_user_by_id(user_id)
            if user and user[3] == 1:  # если забанен
                if update.message:
                    await update.message.answer("⛔ Вы заблокированы.")
                elif update.callback_query:
                    await update.callback_query.answer("⛔ Вы заблокированы.", show_alert=True)
                raise CancelHandler()
