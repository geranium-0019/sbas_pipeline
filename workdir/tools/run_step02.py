from pathlib import Path

import yaml

from s1_sbas_download import sbas_select_and_download


def main() -> None:
    # Resolve config relative to this repo/workdir to avoid depending on CWD.
    config_path = Path(__file__).parent.parent / "config.yaml"
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    project_dir = Path(cfg.get("project_dir", "")).expanduser().resolve()
    if not str(project_dir):
        raise ValueError("config.yaml must set: project_dir")

    res = sbas_select_and_download(cfg, project_dir)
    print(res)

if __name__ == "__main__":
    main()
