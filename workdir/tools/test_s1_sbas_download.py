#!/usr/bin/env python3
"""Test s1_sbas_download.py functionality"""

from pathlib import Path
import yaml
import sys

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

from s1_sbas_download import sbas_select_and_download

def main():
    # Use jakarta_s1 config as test case
    config_path = Path(__file__).parent.parent / "jakarta_s1" / "config.yaml"
    
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1
    
    print(f"Loading config from: {config_path}")
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    
    print("\nConfiguration:")
    print(f"  AOI: {cfg['aoi_bbox']}")
    print(f"  Date range: {cfg['date_start']} to {cfg['date_end']}")
    print(f"  Orbit: {cfg['orbit_direction']}")
    print(f"  Dry run: {cfg['s1_download'].get('dry_search_only', False)}")
    print(f"  AOI shrink: {cfg['s1_download'].get('aoi_shrink_m', 0)} m")
    
    # Project directory is where config.yaml lives
    project_dir = config_path.parent
    
    print(f"\nProject directory: {project_dir}")
    print("\nStarting SBAS search and selection...")
    print("-" * 60)
    
    try:
        result = sbas_select_and_download(cfg, project_dir)
        
        print("\n" + "=" * 60)
        print("RESULTS:")
        print("=" * 60)
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        if result.get('pairs_file'):
            print(f"\n✓ Pairs file created: {result['pairs_file']}")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())