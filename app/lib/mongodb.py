from pfmongo import pfmongo
from pfmongo.commands.dbop import connect as database
from pfmongo.commands.clop import connect as collection
from pfmongo.commands.docop import add as datacol, get
from pfmongo.models.responseModel import mongodbResponse
import json
from typing import Optional, Collection


async def db_init(
    llm_name: str, session_id: str
) -> tuple[mongodbResponse, mongodbResponse]:
    """
    Initialize the MongoDB database and collection.

    :param llm_name: Name of the LLM (used as the database name).
    :param session_id: Unique ID for the session (used as the collection name).
    :return: An object tuple of the LLM database and session collection response.
    """
    try:
        # Create or connect to the database
        db: mongodbResponse = await database.connectTo_asModel(
            database.options_add(llm_name, pfmongo.options_initialize())
        )

        # Create or connect to the collection
        col: mongodbResponse = await collection.connectTo_asModel(
            collection.options_add(session_id, pfmongo.options_initialize())
        )
        print(f"Initialized database '{llm_name}' with collection '{session_id}'.")
        return db, col

    except Exception as e:
        raise RuntimeError(f"Failed to initialize MongoDB: {e}")


async def db_contains(id: str) -> mongodbResponse:
    return await get.documentGet_asModel(
        get.options_add(id, pfmongo.options_initialize())
    )


async def db_add(
    data: dict[str, str | dict | Collection[str]], id: str
) -> mongodbResponse:
    result: mongodbResponse = await datacol.documentAdd_asModel(
        datacol.options_add(json.dumps(data), id, pfmongo.options_initialize())
    )
    return result
