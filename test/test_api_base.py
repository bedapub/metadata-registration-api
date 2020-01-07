import urllib


class AbstractTest(object):

    @classmethod
    def clear_collection(cls, entrypoint="/properties/", deprecated=True):
        """ Remove all entries"""
        res = cls.get_ids(cls.app, entrypoint, deprecated)

        if res.status_code != 200:
            raise Exception(f"Could not access data {res.json}")

        if res.json:
            for d in res.json:
                if not d:
                    continue
                res = cls.app.delete(f"{entrypoint}id/{d['id']}?complete=True", follow_redirects=True)

                if res.status_code != 200:
                    raise Exception(f"Could not delete file (id={d['id']}) in {entrypoint}. {res.json}")

    @staticmethod
    def get(app, entrypoint, params=None, headers=None):
        p = None
        if params:
            p = urllib.parse.urlencode(params)
        return app.get(f"{entrypoint}?{p}", follow_redirects=True, headers=headers)

    @staticmethod
    def get_ids(app, entrypoint='/properties/', deprecated=False):
        """ Get the id of all properties """
        return AbstractTest.get(app,
                                entrypoint=entrypoint,
                                params={"deprecated": deprecated},
                                headers={"X-Fields": "id"})

    @staticmethod
    def insert(app, data, entrypoint="/properties/", check_status=True):
        """ Insert a new entry """
        res = app.post(f"{entrypoint}", follow_redirects=True, json=data)

        if check_status and res.status_code != 201:
            raise Exception(f"Could not insert property. {res.json}")

        return res
