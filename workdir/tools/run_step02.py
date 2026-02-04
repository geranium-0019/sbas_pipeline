from pathlib import Path
import yaml

from s1_sbas_download import sbas_select_and_download

CONFIG = Path("work/jakarta_s1/config.yaml")
PROJECT_DIR = CONFIG.parent  # project_dir = work/jakarta_s1

def main():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    res = sbas_select_and_download(cfg, PROJECT_DIR)
    print(res)

if __name__ == "__main__":
    main()
