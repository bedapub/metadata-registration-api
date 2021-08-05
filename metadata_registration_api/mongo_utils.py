from pymongo import MongoClient


def get_client(app):
    if app.config["MONGODB_USERNAME"] and app.config["MONGODB_PASSWORD"]:
        return MongoClient(
            host=app.config["MONGODB_HOST"],
            port=app.config["MONGODB_PORT"],
            username=app.config["MONGODB_USERNAME"],
            password=app.config["MONGODB_PASSWORD"],
            authSource=app.config["MONGODB_DB"],
            authMechanism="SCRAM-SHA-1",
        )
    else:
        return MongoClient(
            host=app.config["MONGODB_HOST"],
            port=app.config["MONGODB_PORT"],
            authSource=app.config["MONGODB_DB"],
        )


def get_states(app, q={}):
    """Returns states as list of dict directly from MongoDB"""
    client = get_client(app)
    db = client[app.config["MONGODB_DB"]]
    cur = db[app.config["MONGODB_COL_STATE"]]
    results = cur.find(q)

    return list(results)
