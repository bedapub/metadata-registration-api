from pymongo import MongoClient

from metadata_registration_lib.api_utils import FormatConverter, NestedListEntry

from .model import Study


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


################################################
##### Agregations
################################################
def find_study_id_from_lvl1_uuid(lvl1_prop, lvl1_uuid, prop_name_to_id):
    """Find parent study given a dataset_uuid"""
    study_id = None

    aggregated_studies = get_aggregated_studies(
        prop_map=prop_name_to_id, level_1=lvl1_prop
    )

    for study in aggregated_studies:
        if lvl1_uuid in study[f"{lvl1_prop}s_uuids"]:
            return study["id"]

    return study_id


def find_study_id_and_lvl1_uuid_from_lvl2_uuid(
    lvl1_prop, lvl2_prop, lvl2_uuid, prop_name_to_id, prop_id_to_name
):
    """Find parent study and lvl1 uuid (ex: Dataset) given a lvl2 uuid (ex: Processing event)"""
    study_id = None
    lvl1_uuid = None

    aggregated_studies = get_aggregated_studies(
        prop_map=prop_name_to_id,
        level_1=lvl1_prop,
        level_2=lvl2_prop,
    )

    for potential_study in aggregated_studies:
        if lvl2_uuid in potential_study[f"{lvl2_prop}s_uuids"]:
            study = potential_study
            study_id = study["id"]
            break
    else:
        return study_id, lvl1_uuid

    lvl1_list_entry = NestedListEntry(FormatConverter(prop_id_to_name)).add_api_format(
        study["datasets"]
    )

    for lvl1_nested_entry in lvl1_list_entry.value:
        lvl1_uuid = lvl1_nested_entry.get_entry_by_name("uuid").value
        lvl1_entry = lvl1_nested_entry.get_entry_by_name(f"{lvl2_prop}s")

        try:
            lvl1_entry.value.find_nested_entry("uuid", lvl2_uuid)
            return study_id, lvl1_uuid
        except:
            pass  # Lvl 2 entity not in this lvl 1 entity

    return study_id, lvl1_uuid


def get_aggregated_studies(prop_map, level_1="dataset", level_2=None):
    """
    Super messy and dirty mongoDB aggregation to save time finding a study
    from a dataset_uuid.
    Note to future self: so sorry about that but no worry, Elastic Search will replace that.
    If level_2 = None, only prop1_uuids will be returned
    If level_2 = True, only prop1 entities with at least one prop2 entity will be returned
    """
    # TODO: This should go away when we index all studies in form format with Elastic Search
    prop1 = level_1
    prop1_plur = f"{prop1}s"

    pipeline_lvl1 = [
        # Keep only prop1 entry
        {
            "$addFields": {
                prop1_plur: {
                    "$filter": {
                        "input": "$entries",
                        "as": "entry",
                        "cond": {
                            "$eq": [
                                {"$toString": "$$entry.property"},
                                prop_map[prop1_plur],
                            ]
                        },
                    }
                }
            }
        },
        # Keep studies with at least one prop1
        {"$match": {f"{prop1_plur}.0": {"$exists": True}}},
        # Take first (and only) element of filtered entries
        {"$addFields": {prop1_plur: {"$arrayElemAt": [f"${prop1_plur}", 0]}}},
        # Get the actual list of lvl1 entities from the lvl1 entities entry value
        {"$addFields": {prop1_plur: f"${prop1_plur}.value"}},
        # Prop 1 UUIDs: Keep only prop1_uuid entries (exactly 1)
        {
            "$addFields": {
                f"{prop1_plur}_uuids": {
                    "$map": {
                        "input": f"${prop1_plur}",
                        "as": prop1,
                        "in": {
                            "$filter": {
                                "input": f"$${prop1}",
                                "as": f"{prop1}_entry",
                                "cond": {
                                    "$eq": [
                                        f"$${prop1}_entry.property",
                                        prop_map["uuid"],
                                    ]
                                },
                            }
                        },
                    }
                }
            }
        },
        # prop1 UUIDs: Take first (and only) element of filtered entries
        {
            "$addFields": {
                f"{prop1_plur}_uuids": {
                    "$map": {
                        "input": f"${prop1_plur}_uuids",
                        "as": prop1,
                        "in": {"$arrayElemAt": [f"$${prop1}", 0]},
                    }
                }
            }
        },
        # Prop1 UUIDs: make a flat list of UUIDs
        {
            "$addFields": {
                f"{prop1_plur}_uuids": {
                    "$map": {
                        "input": f"${prop1_plur}_uuids",
                        "as": "uuid_entry",
                        "in": "$$uuid_entry.value",
                    }
                }
            }
        },
    ]

    if level_2 == None:
        pipeline_lvl1_format = [
            # Clean, project only wanted fields
            {
                "$project": {
                    "id": {"$toString": "$_id"},
                    f"{prop1_plur}_uuids": 1,
                    prop1_plur: 1,
                    "_id": 0,
                }
            },
        ]
        pipeline = pipeline_lvl1 + pipeline_lvl1_format
        aggregated_studies = Study.objects().aggregate(pipeline)

        return aggregated_studies

    else:
        prop2 = level_2
        prop2_plur = f"{prop2}s"
        pipeline_lvl2 = [
            # Prop 2 UUIDs: Keep only process_events entries (exactly 1)
            {
                "$addFields": {
                    f"{prop1_plur}_for_{prop2}": {
                        "$map": {
                            "input": f"${prop1_plur}",
                            "as": prop1,
                            "in": {
                                "$filter": {
                                    "input": f"$${prop1}",
                                    "as": f"{prop1}_entry",
                                    "cond": {
                                        "$eq": [
                                            f"$${prop1}_entry.property",
                                            prop_map[prop2_plur],
                                        ]
                                    },
                                }
                            },
                        }
                    }
                }
            },
            # Prop 2 UUIDs: Take first (and only) element of filtered prop 1 entries
            {
                "$addFields": {
                    f"{prop1_plur}_for_{prop2}": {
                        "$map": {
                            "input": f"${prop1_plur}_for_{prop2}",
                            "as": prop1,
                            "in": {"$arrayElemAt": [f"$${prop1}", 0]},
                        }
                    }
                }
            },
            # Prop 2 UUIDs: make a flat list of processing events
            {
                "$addFields": {
                    f"{prop1_plur}_for_{prop2}": {
                        "$map": {
                            "input": f"${prop1_plur}_for_{prop2}",
                            "as": prop1,
                            "in": f"$${prop1}.value",
                        }
                    }
                }
            },
            # Prop 2 UUIDs: Keep only uuid entries (exactly 1)
            {
                "$addFields": {
                    f"{prop1_plur}_for_{prop2}": {
                        "$map": {
                            "input": f"${prop1_plur}_for_{prop2}",
                            "as": prop1,
                            "in": {
                                "$map": {
                                    "input": f"$${prop1}",
                                    "as": prop2,
                                    "in": {
                                        "$filter": {
                                            "input": f"$${prop2}",
                                            "as": f"{prop2}_entry",
                                            "cond": {
                                                "$eq": [
                                                    f"$${prop2}_entry.property",
                                                    prop_map["uuid"],
                                                ]
                                            },
                                        }
                                    },
                                }
                            },
                        }
                    }
                }
            },
            # Prop 2: Take first (and only) element of filtered entries
            {
                "$addFields": {
                    f"{prop1_plur}_for_{prop2}": {
                        "$map": {
                            "input": f"${prop1_plur}_for_{prop2}",
                            "as": prop1,
                            "in": {
                                "$map": {
                                    "input": f"$${prop1}",
                                    "as": prop2,
                                    "in": {"$arrayElemAt": [f"$${prop2}", 0]},
                                }
                            },
                        }
                    }
                }
            },
            # Prop 2 UUIDs: make a flat list of UUIDs (per prop 1)
            {
                "$addFields": {
                    f"{prop2_plur}_uuids": {
                        "$map": {
                            "input": f"${prop1_plur}_for_{prop2}",
                            "as": prop1,
                            "in": {
                                "$map": {
                                    "input": f"$${prop1}",
                                    "as": prop2,
                                    "in": f"$${prop2}.value",
                                }
                            },
                        }
                    }
                }
            },
            # Prop 2 UUIDs: Flatten the UUID list (no separation per prop 1)
            # It also removes the None but I have no idea why
            {"$unwind": f"${prop2_plur}_uuids"},
            {"$unwind": f"${prop2_plur}_uuids"},
            {"$unwind": f"${prop1_plur}_uuids"},
            {"$unwind": f"${prop1_plur}_uuids"},
            {"$unwind": f"${prop1_plur}"},
            {
                "$group": {
                    "_id": "$_id",
                    f"{prop2_plur}_uuids": {"$addToSet": f"${prop2_plur}_uuids"},
                    f"{prop1_plur}_uuids": {"$addToSet": f"${prop1_plur}_uuids"},
                    prop1_plur: {"$addToSet": f"${prop1_plur}"},
                }
            },
            # Clean, project only wanted fields
            {
                "$project": {
                    "id": {"$toString": "$_id"},
                    f"{prop1_plur}_uuids": 1,
                    f"{prop2_plur}_uuids": 1,
                    f"{prop1_plur}": 1,
                    "_id": 0,
                }
            },
        ]
        pipeline = pipeline_lvl1 + pipeline_lvl2
        aggregated_studies = Study.objects().aggregate(pipeline)

        return aggregated_studies
