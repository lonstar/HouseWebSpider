# coding=utf-8
import pymongo


class MongoDb(object):
    def __init__(self, db_name, ip='localhost', port=27017):
        self.conn = pymongo.MongoClient('localhost', 27017)
        self.db = self.conn[db_name]

    def insert(self, collection_name, info):
        collection = self.db[collection_name]
        find_record = collection.find_one(info)
        if find_record is None:
            collection.insert(info)

    def update(self, collection_name, query, update_info):
        collection = self.db[collection_name]
        collection.update(query, {"$set": update_info}, upsert=True)

    def find(self, collection_name, info):
        collection = self.db[collection_name]
        find_record = collection.find_one(info)
        if find_record:
            return True
        return False

    def close(self):
        self.conn.close()
