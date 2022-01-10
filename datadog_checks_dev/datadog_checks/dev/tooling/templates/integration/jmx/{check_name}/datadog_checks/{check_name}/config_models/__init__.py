{license_header}
from .instance import InstanceConfig
from .shared import SharedConfig


class ConfigMixin:
    _config_model_instance: InstanceConfig
    _config_model_shared: SharedConfig

    @property
    def config(self) -> InstanceConfig:
        return self._config_model_instance

    @property
    def shared_config(self) -> SharedConfig:
        return self._config_model_shared
