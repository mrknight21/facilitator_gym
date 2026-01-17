import app.db.mongo as mongo

class BaseRepo:
    def __init__(self, collection: str):
        self.col = mongo.db[collection]
