from os.path import dirname, join

from dynaconf import Dynaconf


BASE_SETTINGS: str = join(dirname(__file__), "settings.yaml")
OVERRIDE_SETTINGS: str = join(dirname(__file__), "settings_override.yaml")


settings: Dynaconf = Dynaconf(
    settings_files=[BASE_SETTINGS, OVERRIDE_SETTINGS],
    merge_enabled=True,
)

