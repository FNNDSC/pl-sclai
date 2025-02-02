# tests/test_config/test_settings.py
import os
import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock
from pydantic import ValidationError
from app.config.settings import (
    App,
    databaseCollection_initialize,
    config_update,
    DEFAULT_META,
    CONFIG_FILE,
)
from app.models.dataModel import DatabaseCollectionModel, DefaultDocument, DocumentData
from pfmongo.models.responseModel import mongodbResponse
import pudb
from pathlib import Path

# Assuming you have a way to clear environment variables before tests
# You might need to adapt this based on your testing setup


def setup_function():
    for k in os.environ:
        if k.startswith("SCL_"):
            del os.environ[k]


def teardown_function():
    for k in os.environ:
        if k.startswith("SCL_"):
            del os.environ[k]


def test_app_default_settings():
    app = App()
    assert app.beQuiet is False
    assert app.noComplain is False
    assert app.detailedOutput is False
    assert app.eventLoopDebug is False
    assert app.fontawesomeUse is True
    assert app.settings_dbcollection == "/claimm/settings"
    assert app.vars_dbcollection == "/claimm/vars"
    assert app.crawl_dbcollection == "/claimm/crawl"


def test_app_env_override():
    os.environ["SCL_BEQUIET"] = "true"
    os.environ["SCL_NOCOMPLAIN"] = "true"
    os.environ["SCL_DETAILEDOUTPUT"] = "true"
    os.environ["SCL_EVENTLOOPDEBUG"] = "true"
    os.environ["SCL_FONTAWESOMEUSE"] = "false"
    os.environ["SCL_SETTINGS_DBCOLLECTION"] = "/test/settings"
    os.environ["SCL_VARS_DBCOLLECTION"] = "/test/vars"
    os.environ["SCL_CRAWL_DBCOLLECTION"] = "/test/crawl"

    app = App()
    assert app.beQuiet is True
    assert app.noComplain is True
    assert app.detailedOutput is True
    assert app.eventLoopDebug is True
    assert app.fontawesomeUse is False
    assert app.settings_dbcollection == "/test/settings"
    assert app.vars_dbcollection == "/test/vars"
    assert app.crawl_dbcollection == "/test/crawl"


def test_app_parse_dbcollection_valid():
    app = App()
    result = app.parse_dbcollection("/testdb/testcollection")
    assert isinstance(result, DatabaseCollectionModel)
    assert result.database == "testdb"
    assert result.collection == "testcollection"


def test_app_parse_dbcollection_invalid():
    app = App()
    with pytest.raises(ValueError, match="Invalid dbcollection format"):
        app.parse_dbcollection("invalid-format")


def test_app_config_case_insensitive():
    os.environ["scl_bequiet"] = "true"
    app = App()
    assert app.beQuiet is True


@pytest.mark.asyncio
async def test_database_collection_initialize_document_valid():
    # Test successful initialization with a valid document
    db_collection = DatabaseCollectionModel(
        database="testdb", collection="testcollection"
    )
    document = DefaultDocument(id="testdoc.json", path="test/path", metadata={})
    with (
        patch("app.config.settings.db_init", new_callable=AsyncMock) as mock_db_init,
        patch(
            "app.config.settings.db_contains", new_callable=AsyncMock
        ) as mock_db_contains,
        patch(
            "app.config.settings.db_docAdd", new_callable=AsyncMock
        ) as mock_db_docAdd,
    ):
        mock_db_init.return_value = (
            mongodbResponse(status=True, message="db_init"),
            mongodbResponse(status=True, message="col_init"),
        )
        mock_db_contains.return_value = mongodbResponse(
            status=False, message="Document not found"
        )
        mock_db_docAdd.return_value = mongodbResponse(
            status=True, message="Document added"
        )

        result = await databaseCollection_initialize(db_collection, document)
        assert result.status is True
        assert result.source == "MongoDB"
        assert "Document added successfully" in result.message


@pytest.mark.asyncio
async def test_database_collection_initialize_document_exists():
    # Test initialization when the document already exists
    db_collection = DatabaseCollectionModel(
        database="testdb", collection="testcollection"
    )
    document = DefaultDocument(id="testdoc.json", path="test/path", metadata={})
    with (
        patch("app.config.settings.db_init", new_callable=AsyncMock) as mock_db_init,
        patch(
            "app.config.settings.db_contains", new_callable=AsyncMock
        ) as mock_db_contains,
    ):
        mock_db_init.return_value = (
            mongodbResponse(status=True, message="db_init"),
            mongodbResponse(status=True, message="col_init"),
        )
        mock_db_contains.return_value = mongodbResponse(
            status=True, message="Document found"
        )

        result = await databaseCollection_initialize(db_collection, document)
        assert result.status is True
        assert result.source == "MongoDB"
        assert "Document already exists" in result.message


@pytest.mark.asyncio
async def test_database_collection_initialize_invalid_document():
    # Test initialization with an invalid document (not JSON serializable)
    db_collection = DatabaseCollectionModel(
        database="testdb", collection="testcollection"
    )
    document = DefaultDocument(
        id="testdoc.json", path="test/path", metadata={"invalid": lambda x: x}
    )
    result = await databaseCollection_initialize(db_collection, document)
    assert result.status is False
    assert result.source == "Validation"
    assert "Document contains invalid JSON" in result.message


@pytest.mark.asyncio
async def test_database_collection_initialize_mongodb_failure():
    # Test initialization when MongoDB initialization fails
    db_collection = DatabaseCollectionModel(
        database="testdb", collection="testcollection"
    )
    document = DefaultDocument(id="testdoc.json", path="test/path", metadata={})
    with (
        patch("app.config.settings.db_init", new_callable=AsyncMock) as mock_db_init,
        patch(
            "app.config.settings._initialize_local", new_callable=AsyncMock
        ) as mock_initialize_local,
    ):
        mock_db_init.side_effect = Exception("MongoDB connection failed")
        mock_initialize_local.return_value = InitializationResult(
            status=True, source="Local", message="Document stored locally"
        )
        result = await databaseCollection_initialize(db_collection, document)
        assert result.status is True
        assert result.source == "Local"
        assert "Document stored locally" in result.message


@pytest.mark.asyncio
async def test_initialize_local_success(tmp_path):
    # Test successful local initialization
    document = DefaultDocument(
        id="testdoc.json", path="testdb/testcollection", metadata={}
    )
    result = await databaseCollection_initialize(
        DatabaseCollectionModel(database="testdb", collection="testcollection"),
        document,
    )
    assert result.status is True
    assert result.source == "Local"
    assert "Document stored at" in result.message


@pytest.mark.asyncio
async def test_initialize_local_failure(tmp_path):
    # Test local initialization failure (e.g., permission error)
    document = DefaultDocument(
        id="testdoc.json", path="testdb/testcollection", metadata={}
    )
    with patch("pathlib.Path.mkdir") as mock_mkdir:
        mock_mkdir.side_effect = OSError("Permission denied")
        result = await databaseCollection_initialize(
            DatabaseCollectionModel(database="testdb", collection="testcollection"),
            document,
        )
        assert result.status is False
        assert result.source == "Local"
        assert "Failed to store document locally" in result.message


@pytest.mark.asyncio
async def test_config_update_mongodb_success():
    # Test successful configuration update in MongoDB
    with (
        patch(
            "app.config.settings.db_contains", new_callable=AsyncMock
        ) as mock_db_contains,
        patch(
            "app.config.settings.db_docAdd", new_callable=AsyncMock
        ) as mock_db_docAdd,
    ):
        mock_db_contains.return_value = mongodbResponse(
            status=True,
            message=json.dumps(
                {
                    "metadata": {"keys": {"OpenAI": "", "Claude": ""}, "use": "OpenAI"},
                    "path": DEFAULT_META.path,
                    "id": DEFAULT_META.id,
                }
            ),
        )
        mock_db_docAdd.return_value = mongodbResponse(
            status=True, message="Document updated"
        )

        result = await config_update(llm="OpenAI", key="new_key")
        assert result is True


@pytest.mark.asyncio
async def test_config_update_mongodb_failure():
    # Test configuration update failure in MongoDB
    with (
        patch(
            "app.config.settings.db_contains", new_callable=AsyncMock
        ) as mock_db_contains,
        patch(
            "app.config.settings.db_docAdd", new_callable=AsyncMock
        ) as mock_db_docAdd,
    ):
        mock_db_contains.return_value = mongodbResponse(
            status=True,
            message=json.dumps(
                {
                    "metadata": {"keys": {"OpenAI": "", "Claude": ""}, "use": "OpenAI"},
                    "path": DEFAULT_META.path,
                    "id": DEFAULT_META.id,
                }
            ),
        )
        mock_db_docAdd.return_value = mongodbResponse(
            status=False, message="Failed to update document"
        )

        result = await config_update(llm="OpenAI", key="new_key")
        assert result is False


@pytest.mark.asyncio
async def test_config_update_local_success(tmp_path):
    # Test successful local configuration update
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "metadata": {"keys": {"OpenAI": "", "Claude": ""}, "use": "OpenAI"},
                "path": DEFAULT_META.path,
                "id": DEFAULT_META.id,
            }
        )
    )

    with (
        patch(
            "app.config.settings.db_contains", new_callable=AsyncMock
        ) as mock_db_contains,
        patch("app.config.settings.CONFIG_FILE", config_file),
    ):
        mock_db_contains.return_value = mongodbResponse(
            status=False, message="MongoDB unavailable"
        )
        result = await config_update(llm="Claude", key="new_key")
        assert result is True
        updated_config = json.loads(config_file.read_text())
        assert updated_config["metadata"]["use"] == "Claude"
        assert updated_config["metadata"]["keys"]["Claude"] == "new_key"


@pytest.mark.asyncio
async def test_config_update_local_failure(tmp_path):
    # Test local configuration update failure (e.g., permission error)
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "metadata": {"keys": {"OpenAI": "", "Claude": ""}, "use": "OpenAI"},
                "path": DEFAULT_META.path,
                "id": DEFAULT_META.id,
            }
        )
    )

    with (
        patch(
            "app.config.settings.db_contains", new_callable=AsyncMock
        ) as mock_db_contains,
        patch("app.config.settings.CONFIG_FILE", config_file),
        patch("pathlib.Path.write_text") as mock_write_text,
    ):
        mock_db_contains.return_value = mongodbResponse(
            status=False, message="MongoDB unavailable"
        )
        mock_write_text.side_effect = OSError("Permission denied")
        result = await config_update(llm="Claude", key="new_key")
        assert result is False


@pytest.mark.asyncio
async def test_config_update_missing_llm_for_key():
    # Test that config_update raises an error when a key is provided without an LLM
    with pytest.raises(ValueError, match="You must specify '--use' with '--key'"):
        await config_update(llm=None, key="some_key")


@pytest.mark.asyncio
async def test_config_update_local_missing_llm_for_key(tmp_path):
    pudb.set_trace()
    # Test that config_update raises an error when a key is provided without an LLM in the local fallback scenario
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(DEFAULT_META.model_dump()))

    with (
        patch(
            "app.config.settings.db_contains", new_callable=AsyncMock
        ) as mock_db_contains,
        patch("app.config.settings.CONFIG_FILE", config_file),
    ):
        mock_db_contains.return_value = mongodbResponse(
            status=False, message="MongoDB unavailable"
        )
        with pytest.raises(
            ValueError,
            match="You must specify '--use' with '--key' to associate the key with an LLM",
        ):
            await config_update(llm=None, key="some_key")


if __name__ == "__main__":
    print("Manual testing/debugging")
    pudb.set_trace()
    asyncio.run(test_config_update_local_missing_llm_for_key(Path("/tmp")))
