"""
mongodb.py

This module provides utility functions for interacting with MongoDB, including:
- Database and collection initialization.
- Document addition and retrieval.

Features:
- Uses Pydantic models for structured responses and validation.
- Handles MongoDB operations with proper error reporting.

Usage:
Import the functions in this module to manage MongoDB databases and collections.
"""

import json
from typing import Any
from pfmongo import pfmongo
from pfmongo.commands.dbop import connect as database
from pfmongo.commands.clop import connect as collection
from pfmongo.commands.docop import add as datacol, get
from pfmongo.commands.document import delete as deldoc
from pfmongo.commands.docop import showAll
from pfmongo.models.responseModel import mongodbResponse
from app.models.dataModel import DbInitResult, DocumentData, DatabaseCollectionModel
from app.lib.log import LOG


async def db_init(db_collection: DatabaseCollectionModel) -> DbInitResult:
    """
    Initialize a MongoDB database and collection.

    :param db_collection: DatabaseCollectionModel containing database and collection names.
    :return: DbInitResult containing database and collection responses.
    """
    try:
        db_response: mongodbResponse = await database.connectTo_asModel(
            database.options_add(db_collection.database, pfmongo.options_initialize())
        )

        col_response: mongodbResponse = await collection.connectTo_asModel(
            collection.options_add(
                db_collection.collection, pfmongo.options_initialize()
            )
        )

        LOG(
            f"Initialized database '{db_collection.database}' with collection '{db_collection.collection}'."
        )
        return DbInitResult(db_response=db_response, col_response=col_response)

    except Exception as e:
        LOG(f"Error initializing MongoDB: {e}")
        return DbInitResult(
            db_response=mongodbResponse(
                status=False,
                message=f"Error initializing database: {e}",
                response={},
                exitCode=1,
            ),
            col_response=mongodbResponse(
                status=False,
                message=f"Error initializing collection: {e}",
                response={},
                exitCode=1,
            ),
        )


async def db_contains(document_id: str) -> mongodbResponse:
    """
    Check if a document exists in a MongoDB collection.

    :param document_id: The unique identifier of the document.
    :return: mongodbResponse containing the operation result.
    """
    try:
        return await get.documentGet_asModel(
            get.options_add(document_id, pfmongo.options_initialize())
        )
    except Exception as e:
        LOG(f"Error checking document existence: {e}")
        return mongodbResponse(
            status=False,
            message=f"Error checking document existence: {e}",
            response={},
            exitCode=1,
        )


async def db_showAll() -> mongodbResponse:
    """
    Retrieve all documents from the MongoDB collection.

    :return: mongodbResponse containing the list of all documents.
    """
    try:
        result: mongodbResponse = await showAll.showAll_asModel(
            showAll.options_add("_id", pfmongo.options_initialize())
        )
        return result
    except Exception as e:
        LOG(f"Error retrieving all documents: {e}")
        return mongodbResponse(
            status=False,
            message=f"Error retrieving all documents: {e}",
            response={},
            exitCode=1,
        )


async def db_docAdd(document_data: DocumentData) -> mongodbResponse:
    """
    Add a document to a MongoDB collection.

    :param document_data: DocumentData containing the document and its identifier.
    :return: mongodbResponse with the result of the addition operation.
    """
    try:
        result: mongodbResponse = await datacol.documentAdd_asModel(
            datacol.options_add(
                json.dumps(document_data.data),
                document_data.id,
                pfmongo.options_initialize(),
            )
        )
        return result
    except Exception as e:
        LOG(f"Error adding document to MongoDB: {e}")
        return mongodbResponse(
            status=False,
            message=f"Error adding document to MongoDB: {e}",
            response={},
            exitCode=1,
        )


async def db_docDel(document_data: DocumentData) -> mongodbResponse:
    """
    Delete a document from a MongoDB collection.

    :param document_data: DocumentData containing the document and its identifier.
    :return: mongodbResponse with the result of the deletion operation.
    """
    try:
        result: mongodbResponse = await deldoc.deleteDo_asModel(
            deldoc.options_add(document_data.id, pfmongo.options_initialize())
        )
        return result
    except Exception as e:
        LOG(f"Error deleting document from MongoDB: {e}")
        return mongodbResponse(
            status=False,
            message=f"Error deleting document from MongoDB: {e}",
            response={},
            exitCode=1,
        )
