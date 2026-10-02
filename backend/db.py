from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def database(url):
    engine = create_engine(url, pool_pre_ping=True)
    return engine, sessionmaker(engine, expire_on_commit=False)
