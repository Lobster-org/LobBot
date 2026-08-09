from app.database.mongodb import mongodb


def get_database():

    return mongodb.get_database()