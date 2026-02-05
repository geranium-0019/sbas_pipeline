# Time Series InSAR with ISCE2 + MintPy

![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![ISCE2](https://img.shields.io/badge/ISCE2-Supported-green)
![MintPy](https://img.shields.io/badge/MintPy-Supported-green)

このプロジェクトは、**ISCE2** と **MintPy** を使用した時系列InSAR解析のためのDockerベース開発環境です。Sentinel-1データのダウンロードから処理まで、研究者が簡単に利用できるパイプラインを提供します。

## 🎯 目的

- **ISCE2** + **MintPy** を使った時系列InSAR解析の環境を簡単にセットアップ
- Sentinel-1データの自動ダウンロード機能
- 設定ファイルベースのバッチ処理パイプライン
- 他の研究者・ユーザーが簡単に再現できる環境

## 📋 機能

- ✅ **Docker環境**: ISCE2, MintPy, SNAPHU, GDALなどを含む完全な処理環境
- ✅ **Sentinel-1ダウンロード**: ASFからの自動データダウンロード機能
- ✅ **設定ベース処理**: YAMLファイルによる柔軟なパラメータ設定  
- ✅ **時系列解析パイプライン**: stackSentinel.pyの自動実行スクリプト生成
- ✅ **可視化ツール**: 結果の可視化・GIF作成機能
- ✅ **VS Code統合**: Dev Containerによる開発環境

## 🛠️ 必要環境

- **Docker**: 20.10以降
- **Docker Compose**: 2.0以降  
- **VS Code** (推奨): Dev Container拡張機能
- **十分なストレージ**: Sentinel-1データ用（数十GB～数百GB）

## 🚀 セットアップ

### 🔥 クイックスタート（推奨）

**ワンコマンドで環境をセットアップ:**

```bash
git clone <このリポジトリのURL>
cd time_series_insar
./setup.sh
```

`setup.sh` が以下を自動実行します：
- ✅ Docker/Docker Composeの確認
- ✅ 必要ディレクトリの作成
- ✅ `.env`ファイルの生成
- ✅ 設定テンプレートの作成
- ✅ Docker環境のビルド

### 手動セットアップ

#### 1. リポジトリのクローン

```bash
git clone <このリポジトリのURL>
cd time_series_insar
```

#### 2. 環境変数の設定

`.env` ファイルを作成してEarthdata認証情報を設定：

```bash
# .env ファイル
EARTHDATA_USER=your_username
EARTHDATA_PASS=your_password

# SBAS Time Series InSAR Pipeline (ISCE2 + MintPy)

![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![ISCE2](https://img.shields.io/badge/ISCE2-Supported-green)
![MintPy](https://img.shields.io/badge/MintPy-Supported-green)

このリポジトリは、Sentinel-1 IW SLC を対象に **SBAS (Small Baseline Subset)** の時系列InSARを実行するための、Dockerベースのパイプラインです。

パイプライン本体は `workdir/run_pipeline.py` で、設定 `config.yaml` を元に `steps/` を順に実行し、各Stepの完了状態を `<project_dir>/.state/` に保存します。

## 特徴

- Dockerだけで ISCE2 / MintPy / SNAPHU / GDAL 等を揃えられる
- `config.yaml` 1つで検索→SBASネットワーク構築→ダウンロード→ISCE2→MintPy まで実行
- Step単位で再実行・部分実行ができる（`.state` によるスキップ）

## 必要環境

- Docker
- Docker Compose（`docker compose` が使えること）
- ストレージ（解析範囲/期間によって数十GB〜）

## クイックスタート

### 1) 初期セットアップ（推奨）

```bash
./setup.sh
```

`setup.sh` は対話的に以下を行います。

- `.env` の作成/更新（認証情報テンプレート、PROJECT_NAME など）
- `workdir/config.yaml` の `project_dir` を `/work/<PROJECT_NAME>` に更新
- 必要に応じて `docker-compose.override.yml` を生成（外部ディスクを `/work/<PROJECT_NAME>` にマウント）

### 2) コンテナ起動

```bash
docker compose up -d --build
```

### 3) コンテナに入る

```bash
docker compose exec app bash
```

### 4) パイプライン実行

コンテナ内で:

```bash
cd /work
python run_pipeline.py --config config.yaml
```

成果物は `config.yaml` の `project_dir`（例: `/work/<PROJECT_NAME>`）配下に作成されます。

## ディレクトリとマウントの考え方

- ホストの `./workdir/` はコンテナの `/work` にマウントされます（`docker-compose.yml`）。
- 解析プロジェクトの出力先は `project_dir` で指定します。
  - 例: `project_dir: /work/jakarta_s1`
  - `/work` 配下にすることで、コンテナ削除後もホスト側に成果が残ります。

プロジェクトディレクトリの標準構成（例）:

```
<project_dir>/
  config.resolved.yaml        # Step01: 実行時設定のスナップショット
  logs/pipeline.log           # パイプラインログ
  .state/                     # Step完了状態と中間メタ
    01_prepare.json
    02_download_s1.json
    sbas_pairs.json           # Step02: 選択シーン・ペア・bboxなど
  data/
    s1_slc/                   # Step02: ダウンロードされた SAFE/zip
    dem/                      # Step03: DEM
    orbit/                    # Step04: EOF
    aux/                      # Step05: stackSentinel用 AUX
  isce2/                      # Step05/06: stackSentinel の作業ディレクトリ
  mintpy/                     # Step07: MintPy 実行ディレクトリ
```

## 設定ファイル（config.yaml）

最低限必要なのは以下です。

```yaml
project_dir: /work/<PROJECT_NAME>
aoi_bbox: [W, S, E, N]
date_start: "YYYY-MM-DD"
date_end:   "YYYY-MM-DD"
orbit_direction: "ASC"   # or "DESC" or "BOTH"
```

### `s1_download`（ASF検索/ダウンロード）

主にStep02で使用します。

- `s1_download.out_dir`: `project_dir` からの相対パス（既定: `data/s1_slc`）
- `s1_download.aoi_shrink_m`: AOIを内側に縮めて候補数を減らす（m）
- `s1_download.dry_search_only`: `true` にすると検索・選択のみでダウンロードしない
- `s1_download.skip_existing`: 既存ファイルがあればスキップ

認証はコンテナ内の `~/.netrc` を使用します（下の「認証」参照）。

### `sbas`（ネットワーク/シーン間引き）

Step02でSBASペアを作ります。

- `sbas.k_neighbors`: k近傍（時系列の密度）
- `sbas.max_temporal_days`: 最大時間間隔（日）
- `sbas.ensure_chain`: 連結性確保（隣接時刻ペアを追加）
- `sbas.enforce_same_frame`: 同一frame/sliceのみ使用（既定: true）
- `sbas.thin_acquisitions.min_repeat_days`: 観測日を間引く（例: 12でほぼ隔回）

### `dem`（DEMダウンロード）

Step03は `dem.py` を呼び出します。

- `dem.url`: 取得元URL（省略時: `https://step.esa.int/auxdata/dem/SRTMGL1/`）

### `orbits`（EOFダウンロード）

Step04は `fetchOrbit_asf.py` を使ってEOFを落とします。

- `orbits.prefer`: `precise`（POEORB）または `restituted`（RESORB）
- `orbits.only_selected`: Step02で選ばれたシーンのみ対象（既定: true）

### `isce2`（stackSentinelパラメータ）

未指定でも動くようにデフォルトがありますが、結果が安定しない場合は明示を推奨します。

重要オプション例:

```yaml
isce2:
  workflow: interferogram
  swath_num: "1 2 3"
  coregistration: NESD
  reference_date: auto      # or "YYYYMMDD"
  range_looks: 9
  azimuth_looks: 3
  filter_strength: 0.5
  unw_method: snaphu
  num_connections: 2
  num_proc: 8
  num_proc4topo: 4

  # 推奨: bboxを明示（Step02のunion bboxは広がりすぎる場合がある）
  # bbox: [S, N, W, E]
```

## 実行方法（部分実行/再実行）

すべてコンテナ内 `/work` で実行する想定です。

### 全Stepを実行

```bash
python run_pipeline.py --config config.yaml
```

### Stepを指定して実行

```bash
python run_pipeline.py --config config.yaml --only-steps 02_download_s1 03_download_dem
```

### 範囲を指定して実行

```bash
python run_pipeline.py --config config.yaml --from-step 05_config_stack --until-step 07_run_mintpy
```

### 既にdoneのStepも強制再実行

```bash
python run_pipeline.py --config config.yaml --force
```

### ドライラン（コマンドだけ表示）

```bash
python run_pipeline.py --config config.yaml --dry-run
```

## 認証（Earthdata / Copernicus）

Sentinel-1ダウンロードは `~/.netrc` を参照します。

- コンテナ起動時に `init.sh` が `.env` の `EARTHDATA_USER/EARTHDATA_PASS` から `~/.netrc` を自動生成します。
- `.env` の中身はコミットしないでください（このリポジトリでは `.gitignore` 対象）。

`.netrc` の形式（例）:

```
machine urs.earthdata.nasa.gov login <user> password <pass>
```

## トラブルシューティング

### Step02: 候補が多すぎる / 検索が重い

- `s1_download.dry_search_only: true` でまず選択だけ確認
- `s1_download.aoi_shrink_m` を増やす（例: 2000→5000）
- `date_start/date_end` を短くする

### Step02: frameメタが無くて落ちる

デフォルトで `sbas.enforce_same_frame: true` なので、ASF結果にframe情報が無い場合にエラーになります。

- AOI/期間を絞って再検索
- どうしても必要なら `sbas.enforce_same_frame: false`（推奨はしません）

### Step05: stackSentinelで "dates covering the bbox (0)" など

Step02の `selected_bbox` は union bbox で広がりやすく、共通オーバーラップを外すことがあります。

- `isce2.bbox: [S, N, W, E]` を明示して、オーバーラップ領域に寄せる
- `aoi_bbox` を小さめにする

### Step06: 途中で落ちる / 再開したい

- 失敗したStepだけ `--only-steps` / `--from-step` で再実行
- Stepを最初からやり直す場合は `--force` か、`<project_dir>/.state/<step>.json` を削除

### Step07: MintPyが入力ファイルを見つけない

Step07は `mintpy/smallbaselineApp.cfg` を生成後、`workdir/smallbaselineApp.cfg` を参照して「パス系キーのみ」上書きします。

- Step06が完了して `isce2/merged` などが生成されているか確認
- `workdir/smallbaselineApp.cfg` の想定ディレクトリ（`<project_dir>/isce2/mintpy`）が存在するか確認

## 参考

- ISCE2: https://github.com/isce-framework/isce2
- MintPy: https://github.com/insarlab/MintPy
- ASF Search: https://search.asf.alaska.edu/
