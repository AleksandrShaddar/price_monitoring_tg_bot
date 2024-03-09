import asyncio

from config.logger import setup_logger
from db.crud_operations import ProductsCRUD
from src.notifications.utils import send_message_price_changed

logger = setup_logger(__name__)


class PriceComparer:
    @classmethod
    def compare_prices_and_notify_user(cls, is_any_change: bool, threshold_price: int,
                                       product_last_price: int, product_new_price: int, product_id: int,
                                       chat_id: int, product_url: str, product_name: str):
        cls._validate_is_any_change(is_any_change)
        threshold_price = int(threshold_price)
        product_last_price = int(product_last_price)
        product_new_price = int(product_new_price)
        # cls._validate_int(threshold_price) #// TODO исправить в бд на инт
        # cls._validate_int(product_last_price)
        # cls._validate_int(product_new_price)
        cls._validate_int(chat_id)
        cls._validate_int(product_id)

        is_price_has_changed = cls._compare(product_new_price, product_last_price)

        if not is_price_has_changed:  # возвращает None чтобв прекратить дальнейшее выполнение
            return

        cls._notify_user(product_last_price=product_last_price,
                         product_new_price=product_new_price,
                         chat_id=chat_id,
                         product_url=product_url,
                         product_name=product_name)

        if is_any_change:
            logger.debug("Цена изменилась!")
            ProductsCRUD.set_new_product_price(product_id=product_id, new_price=product_new_price)

        elif product_new_price <= threshold_price:
            logger.info("Цена достигла нужного занчения!")
            ProductsCRUD.set_new_product_price(product_id=product_id, new_price=product_new_price)
            # удалить эту напоминалку

    @classmethod
    def _compare(cls, new_price: int, product_last_price: int) -> bool:
        """Возвращает True если цена изменилась, иначе - False"""
        if not (isinstance(new_price, int) and isinstance(product_last_price, int)):
            raise ValueError
        return new_price != product_last_price

    @classmethod
    def _prepare_message_text(cls, product_name: str, product_url: str,
                              old_price: int, new_price: int):
        price_change = cls._get_price_change(old_price, new_price)
        message_text = (f'[{product_name}]({product_url})\n'
                        f'{price_change}')
        return message_text

    @classmethod
    def _get_price_change(cls, old_price, new_price) -> str:
        if old_price == new_price:
            raise ValueError('Price didnt change!')

        change_amount = new_price - old_price
        change_percent = (change_amount / abs(old_price)) * 100

        if change_amount > 0:
            mes = f" 🟥 Цена увеличилась на {abs(change_amount)} руб ({round(change_percent, 1)} %)\n"
        else:
            mes = f" 🟩 Цена уменьшилась на {abs(change_amount)} руб ({round(change_percent, 1)} %)\n"
        return mes + f'Старая цена: {old_price}\n' + f'Новая цена: {new_price}'

    @classmethod
    def _notify_user(cls, product_last_price,
                     product_new_price,
                     chat_id,
                     product_url,
                     product_name):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            cls._notify_user_async(product_last_price, product_new_price, chat_id, product_url, product_name))

    @classmethod
    async def _notify_user_async(cls, product_last_price,
                                 product_new_price,
                                 chat_id,
                                 product_url,
                                 product_name):
        message_text = cls._prepare_message_text(product_name=product_name,
                                                 product_url=product_url,
                                                 old_price=product_last_price,
                                                 new_price=product_new_price)
        await send_message_price_changed(chat_id=chat_id, message_text=message_text)

    @classmethod
    def _validate_is_any_change(cls, value):
        if not isinstance(value, bool):
            raise ValueError(f'{value} not bool!')

    @classmethod
    def _validate_int(cls, number):
        if not isinstance(number, int):
            raise ValueError(f'{number} not int!')
