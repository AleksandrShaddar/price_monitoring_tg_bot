from contextlib import contextmanager
from typing import Union

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from config.database_config import db_session
from config.logger import setup_logger
from db.models import UserProducts, Users, Products

logger = setup_logger(__name__)


@contextmanager
def handle_database_errors():
    try:
        yield
    except SQLAlchemyError as e:
        logger.warning(f"Ошибка базы данных: {e}")


def database_operation(func):
    def wrapper(*args, **kwargs):
        with handle_database_errors():
            return func(*args, **kwargs)

    return wrapper


class UsersCRUD:
    @classmethod
    @database_operation
    def add_new_user_and_get_user_id(cls, telegram_id: int) -> int:
        cls._validate_telegram_id(telegram_id)

        with db_session() as session:
            statement = select(Users).filter_by(telegram_id=telegram_id)
            existing_user = session.execute(statement).scalars().one_or_none()

            if existing_user:
                return existing_user.id

            new_user = Users(telegram_id=telegram_id)
            session.add(new_user)
            session.commit()
            return new_user.id

    @staticmethod
    def _validate_telegram_id(telegram_id: int):
        if not isinstance(telegram_id, int):
            logger.warning(f'telegram_id {telegram_id} должен быть целым числом')
            raise ValueError("telegram_id должен быть целым числом")


class ProductsCRUD:
    @classmethod
    @database_operation
    def add_new_product(cls, product_url: str, last_price: float, product_name: str) -> Products.id:

        cls._validate_product_url(product_url)
        cls._validate_last_price(last_price)
        cls._validate_product_name(product_name)

        with db_session() as session:
            product = session.query(Products).filter_by(url=product_url).first()

            if not product:
                product = Products(url=product_url, last_price=last_price, product_name=product_name)
                session.add(product)
                session.commit()
                return product.id

            product.last_price = last_price
            product.product_name = product_name
            session.commit()
            return product.id

    @classmethod
    @database_operation
    def get_product_id(cls, product_url: str) -> int | None:
        cls._validate_product_url(product_url)

        with db_session() as session:
            product = session.query(Products).filter_by(url=product_url).first()
            return product.id if product else None

    @classmethod
    @database_operation
    def set_new_product_price(cls, product_id: int, new_price: float | int):
        cls._validate_product_id(product_id)
        cls._validate_last_price(new_price)
        with db_session() as session:
            product = session.query(Products).get(product_id)
            if product:
                product.last_price = new_price
                session.commit()
            else:
                logger.info(f'Ошибка изменения строки {product_id}')
                raise ValueError('Продукта в БД нет!')

    @staticmethod
    def _validate_product_url(product_url):
        if not isinstance(product_url, str) or not product_url:
            logger.warning(f'product_url {product_url} должен быть непустой строкой')
            raise ValueError("product_url должен быть непустой строкой")

    @staticmethod
    def _validate_last_price(last_price):
        if not isinstance(last_price, (int, float)) or last_price < 0:
            logger.warning(f'last_price {last_price} должен быть неотрицательным числом')
            raise ValueError("last_price должен быть неотрицательным числом")

    @staticmethod
    def _validate_product_name(product_name):
        if not isinstance(product_name, str) or not product_name:
            logger.warning(f'product_name {product_name} должен быть неотрицательным числом')
            raise ValueError("product_name должен быть непустой строкой")

    @staticmethod
    def _validate_product_id(product_id):
        if not isinstance(product_id, int):
            logger.warning(f'product_id {product_id} должен быть int')
            raise ValueError("product_id должен быть int")


class UserProductsCRUD:
    @staticmethod
    @database_operation
    def get_user_products_for_handler(telegram_id: int = None) -> UserProducts:
        if not telegram_id:
            raise ValueError # why this error throw
        with db_session() as session:
            query = (
                select(UserProducts)
                .options(joinedload(UserProducts.products),
                         joinedload(UserProducts.users))
                .where(UserProducts.users.has(telegram_id=telegram_id))
            )
            result = session.execute(query).scalars().all()
            return result

    @staticmethod
    @database_operation
    def get_user_products_for_monitoring():
        with db_session() as session:
            query = (
                select(UserProducts)
                .join(UserProducts.products)
                .options(joinedload(UserProducts.products),
                         joinedload(UserProducts.users))
                .order_by(Products.url)
            )
            result = session.execute(query).scalars().all()
            return result

    @staticmethod
    @database_operation  # когда пользователь скидывает ссылку и выбирает что с товаром делать
    def add_user_product(telegram_id: int, product_url: str, is_take_into_account_bonuses: bool,
                         threshold_price: float, last_product_price: float, product_name: str, is_any_change: bool):
        with db_session() as session:
            user_id = UsersCRUD.add_new_user_and_get_user_id(telegram_id=telegram_id)

            product_id = ProductsCRUD.get_product_id(product_url=product_url)
            if product_id is None:
                product_id = ProductsCRUD.add_new_product(product_url=product_url,
                                                          product_name=product_name,
                                                          last_price=last_product_price)

            user_product = UserProducts(user=user_id, product=product_id, is_any_change=is_any_change,
                                        threshold_price=threshold_price,
                                        is_take_into_account_bonuses=is_take_into_account_bonuses)
            session.add(user_product)
            session.commit()

    @staticmethod
    @database_operation
    def delete_user_products(user_product_id: int):
        with db_session() as session:
            user_product = session.get(UserProducts, user_product_id)

            if user_product:
                session.delete(user_product)
                session.commit()
                return user_product
            raise ValueError(f'Invalid user_product_id: {user_product_id}')


# with db_session() as session:
#
#     user_product = session.get(UserProducts, 55)
#     print(user_product)
#     # query = (
    #     select(UserProducts)
    #     .options(joinedload(UserProducts.products),
    #              joinedload(UserProducts.users))
    #     .where(UserProducts.users.has(telegram_id=100))
    # )
    # #
#
#     statement = select(Users).filter_by(telegram_id=100)
#     existing_user = session.execute(statement).scalars().one()
#     print(existing_user)
# #     result = session.execute(query).scalars().all()
#     print(result)
#     for r in result:
#         print(r.users.telegram_id)
#         print(r.products.product_name)

