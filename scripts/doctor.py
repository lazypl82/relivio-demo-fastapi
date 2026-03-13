from __future__ import annotations

from demo_lib import check_app_health, load_demo_config, probe_relivio_runtime


def main() -> None:
    config = load_demo_config()
    print("Relivio demo doctor")
    print(f"- app_base_url={config.app_base_url}")
    print(f"- relivio_api_base_url={config.relivio_api_base_url}")
    print(f"- service_name={config.relivio_service_name}")

    app_ok, app_message = check_app_health(config)
    print(f"- app_health={'OK' if app_ok else 'FAIL'}: {app_message}")

    runtime_ok, runtime_message = probe_relivio_runtime(config)
    print(f"- runtime_probe={'OK' if runtime_ok else 'FAIL'}: {runtime_message}")

    if app_ok and runtime_ok:
        print("doctor_status=ready")
        return

    print("doctor_status=not_ready")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
