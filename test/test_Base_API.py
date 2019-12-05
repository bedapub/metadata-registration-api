class AbstractTest(object):

    @staticmethod
    def clear_collection(app, entrypoint="/properties", deprecate=True):
        """ Remove all entries"""
        res = AbstractTest.get_ids(app, entrypoint, deprecate)

        if res.status_code != 200:
            raise Exception(f"Could not access data {res.json}")

        if res.json:
            for d in res.json:
                if not d:
                    continue
                res = app.delete(f"{entrypoint}/id/{d['id']}?complete=True", follow_redirects=True)

                if res.status_code != 200:
                    raise Exception(f"Could not delete file (id={d['id']}) in {entrypoint}")

    @staticmethod
    def get_ids(app, entrypoint='/properties', deprecate=False):
        """ Get the id of all properties """
        return app.get(f"{entrypoint}?deprecate={deprecate}", follow_redirects=True, headers={"X-Fields": "id"})

    @staticmethod
    def insert(app, data, entrypoint="/properties", check_status=True):
        """ Insert a new entry """
        res = app.post(f"{entrypoint}", follow_redirects=True, json=data)

        if check_status and res.status_code != 201:
            raise Exception(f"Could not insert property. {res.json}")

        return res
