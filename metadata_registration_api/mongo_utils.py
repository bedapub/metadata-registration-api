def get_states(app, q={}):
    """Returns states as list of dict directly from MongoDB"""
    db = app.mongo_client[app.config["MONGODB_DB"]]
    cur = db[app.config["MONGODB_COL_STATE"]]
    results = cur.find(q)

    return list(results)
