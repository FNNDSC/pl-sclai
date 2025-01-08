from pfmongo import pfmongo
from pfmongo.commands.dbop import connect as database
from pfmongo.models import responseModel
from typing import Optional


def db_init(llm_name: str, session_id: str) -> pfmongo.responseModel:
    """
    Initialize the MongoDB database and collection.

    :param llm_name: Name of the LLM (used as the database name).
    :param session_id: Unique ID for the session (used as the collection name).
    :return: A Database object connected to the specified LLM database and session collection.
    """
    try:
        # Create or connect to the database
        db: pfmongo.responseModel = database.sync_connectTo_asModel(
            database.options_add(session_id, pfmongo.options_initialize())
        )

        # Ensure the session collection exists
        db.collection_create(name=session_id)
        print(f"Initialized database '{llm_name}' with collection '{session_id}'.")
        return db

    except Exception as e:
        raise RuntimeError(f"Failed to initialize MongoDB: {e}")
