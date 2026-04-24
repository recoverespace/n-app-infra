from api.lib.tests.fake.types import (
    fake_bool,
    fake_datetime,
    fake_json,
    fake_language,
    fake_model,
    fake_platform,
    fake_store,
    fake_timezone,
    fake_uuid,
    fake_version,
)


def device_factory(**kwargs) -> dict[str, str]:
    return {
        "id": kwargs.get("id", fake_uuid()),
        "installed_at": kwargs.get("installed_at", fake_datetime()),
        "conversion_data": kwargs.get("conversion_data", fake_json()),
        "idfv": kwargs.get("idfv", fake_uuid()),
        "idfa": kwargs.get("idfa", fake_uuid()),
        "limited_ad_tracking": kwargs.get("limited_ad_tracking", fake_bool()),
        "app_version": kwargs.get("app_version", fake_version()),
        "device_model": kwargs.get("device_model", fake_model()),
        "platform": kwargs.get("platform", fake_platform()),
        "store": kwargs.get("store", fake_store()),
        "timezone": kwargs.get("timezone", fake_timezone()),
        "language": kwargs.get("language", fake_language()),
    }
