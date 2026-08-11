from app.core.container import container


def get_database():

    if container.database is None:
        raise RuntimeError("Database is not initialized")

    return container.database
