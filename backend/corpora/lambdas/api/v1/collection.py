import sqlalchemy
from typing import Optional

from flask import make_response, jsonify, g

from ....common.corpora_orm import DbCollection, CollectionVisibility
from ....common.entities import Collection
from ....common.utils.exceptions import ForbiddenHTTPException, ConflictException
from ....api_server.db import dbconnect
from backend.corpora.lambdas.api.v1.authorization import has_scope


def _is_user_owner_or_allowed(user, owner):
    """
    Check if the user has ownership on a collection, or if it has superuser permissions
    """
    return (user and user == owner) or (has_scope("write:collections"))


def _owner_or_allowed(user):
    """
    Returns None if the user is superuser, `user` otherwise. Used for where conditions
    """
    return None if has_scope("write:collections") else user


@dbconnect
def get_collections_list(from_date: int = None, to_date: int = None, user: Optional[str] = None):
    db_session = g.db_session
    all_collections = Collection.list_attributes_in_time_range(
        db_session,
        from_date=from_date,
        to_date=to_date,
        list_attributes=[DbCollection.id, DbCollection.visibility, DbCollection.owner, DbCollection.created_at],
    )

    collections = []
    for coll_dict in all_collections:
        visibility = coll_dict["visibility"]
        owner = coll_dict["owner"]
        if visibility == CollectionVisibility.PUBLIC or _is_user_owner_or_allowed(user, owner):
            collections.append(dict(id=coll_dict["id"], created_at=coll_dict["created_at"], visibility=visibility.name))

    result = {"collections": collections}
    if from_date:
        result["from_date"] = from_date
    if to_date:
        result["to_date"] = to_date

    return make_response(jsonify(result), 200)


@dbconnect
def get_collection_details(collection_uuid: str, visibility: str, user: str):
    db_session = g.db_session
    collection = Collection.get_collection(db_session, collection_uuid, visibility, include_tombstones=True)
    if not collection:
        raise ForbiddenHTTPException()
    if collection.tombstone and visibility == CollectionVisibility.PUBLIC.name:
        result = ""
        response = 410
    else:
        get_tombstone_datasets = (
            _is_user_owner_or_allowed(user, collection.owner) and collection.visibility == CollectionVisibility.PRIVATE
        )
        result = collection.reshape_for_api(get_tombstone_datasets)
        response = 200
        result["access_type"] = "WRITE" if _is_user_owner_or_allowed(user, collection.owner) else "READ"
    return make_response(jsonify(result), response)


@dbconnect
def get_collections_index():
    # TODO (ebezzi): this is very similar to `get_collections_list` above. Eventually they should be consolidated
    db_session = g.db_session

    filtered_collection = Collection.list_attributes_in_time_range(
        db_session,
        filters=[DbCollection.visibility == CollectionVisibility.PUBLIC],
        list_attributes=[DbCollection.id, DbCollection.name, DbCollection.published_at, DbCollection.revised_at],
    )

    return make_response(jsonify(filtered_collection), 200)


@dbconnect
def post_collection_revision(collection_uuid: str, user: str):
    db_session = g.db_session
    collection = Collection.get_collection(
        db_session,
        collection_uuid,
        CollectionVisibility.PUBLIC.name,
        owner=_owner_or_allowed(user),
    )
    if not collection:
        raise ForbiddenHTTPException()
    try:
        collection_revision = collection.revision()
    except sqlalchemy.exc.IntegrityError as ex:
        db_session.rollback()
        raise ConflictException() from ex
    result = collection_revision.reshape_for_api()

    result["access_type"] = "WRITE"
    return make_response(jsonify(result), 201)


@dbconnect
def create_collection(body: object, user: str):
    db_session = g.db_session
    collection = Collection.create(
        db_session,
        visibility=CollectionVisibility.PRIVATE,
        name=body["name"],
        description=body["description"],
        owner=user,
        links=body.get("links", []),
        contact_name=body["contact_name"],
        contact_email=body["contact_email"],
        curator_name=body.get("curator_name", ""),
    )

    return make_response(jsonify({"collection_uuid": collection.id}), 201)


def get_collection_dataset(dataset_uuid: str):
    raise NotImplementedError


@dbconnect
def delete_collection(collection_uuid: str, visibility: str, user: str):
    db_session = g.db_session
    if visibility == CollectionVisibility.PUBLIC.name:
        pub_collection = Collection.get_collection(
            db_session,
            collection_uuid,
            visibility,
            owner=_owner_or_allowed(user),
            include_tombstones=True,
        )
        priv_collection = Collection.get_collection(
            db_session,
            collection_uuid,
            CollectionVisibility.PRIVATE.name,
            owner=_owner_or_allowed(user),
            include_tombstones=True,
        )

        if pub_collection:
            if not pub_collection.tombstone:
                pub_collection.tombstone_collection()
            if priv_collection:
                if not priv_collection.tombstone:
                    priv_collection.delete()
            return "", 204
    else:
        priv_collection = Collection.get_collection(
            db_session,
            collection_uuid,
            CollectionVisibility.PRIVATE.name,
            owner=_owner_or_allowed(user),
            include_tombstones=True,
        )
        if priv_collection:
            if not priv_collection.tombstone:
                priv_collection.delete()
            return "", 204
    return "", 403


@dbconnect
def update_collection(collection_uuid: str, body: dict, user: str):
    db_session = g.db_session
    collection = Collection.get_collection(
        db_session,
        collection_uuid,
        CollectionVisibility.PRIVATE.name,
        owner=_owner_or_allowed(user),
    )
    if not collection:
        raise ForbiddenHTTPException()
    collection.update(**body)
    result = collection.reshape_for_api(tombstoned_datasets=True)
    result["access_type"] = "WRITE"
    return make_response(jsonify(result), 200)
