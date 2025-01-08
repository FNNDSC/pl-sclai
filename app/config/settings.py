from pathlib import Path
import toml
from appdirs import user_config_dir

# Set up the configuration directory and file using appdirs
CONFIG_DIR = Path(user_config_dir("sclai", ""))
CONFIG_FILE = CONFIG_DIR / "config.toml"

def config_initialize() -> None:
    """
    Ensures the configuration directory and file exist. If not, create them with defaults.
    """
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)
    if not CONFIG_FILE.exists():
        default_config = {"use": "OpenAI", "keys": {"OpenAI": "", "Claude": ""}}
        CONFIG_FILE.write_text(toml.dumps(default_config))


def config_update(llm: str | None, key: str | None) -> None:
    """
    Updates the configuration file with the specified LLM and/or API key.

    :param llm: The LLM to use (e.g., OpenAI, Claude).
    :param key: The API key for the specified LLM.
    """
    config = toml.loads(CONFIG_FILE.read_text())

    if llm:
        config["use"] = llm
    if key:
        if llm:
            config["keys"][llm] = key
        else:
            raise ValueError("You must specify '--use' with '--key' to associate the key with an LLM.")

    CONFIG_FILE.write_text(toml.dumps(config))

