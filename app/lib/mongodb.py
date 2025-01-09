from pfmongo import pfmongo
from pfmongo.commands.dbop import connect as database
from pfmongo.commands.clop import connect as collection
from pfmongo.models.responseModel import mongodbResponse
from typing import Optional


async def db_init(llm_name: str, session_id: str) -> mongodbResponse:
    """
    Initialize the MongoDB database and collection.

    :param llm_name: Name of the LLM (used as the database name).
    :param session_id: Unique ID for the session (used as the collection name).
    :return: A Database object connected to the specified LLM database and session collection.
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
        return col

    except Exception as e:
        raise RuntimeError(f"Failed to initialize MongoDB: {e}")
