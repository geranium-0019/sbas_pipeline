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
```

> **注意**: [NASA Earthdata](https://urs.earthdata.nasa.gov/)でアカウント登録が必要です

#### 3. VS Code Dev Containerで起動

```bash
# VS Codeでフォルダを開く
code .

# Command Palette (Ctrl+Shift+P) で以下を実行:
# > Dev Containers: Reopen in Container
```

または、直接Dockerで起動：

```bash
docker compose up -d
docker compose exec mintpy-isce2 bash
```

## 📖 使用方法

### Step 1: Sentinel-1データのダウンロード

1. **ASFでデータ検索**: [ASF Data Search](https://search.asf.alaska.edu/)にアクセス
2. **ジオメトリファイルをダウンロード**: 検索結果をgeojsonで保存
3. **データダウンロード実行**:

```python
# notebooks/download_sentinel-1.ipynb を使用
from tools.download_sentinel import download_s1_slc

# ASFから取得したgeojsonファイルを指定
asf_file = "tools/your_search_results.geojson"
folder_out = "/work/data/sentinel_images"
username = "your_earthdata_username" 
password = "your_earthdata_password"

download_s1_slc(asf_file, folder_out, username, password)
```

### Step 2: 設定ファイルの準備

`config_example.yaml`をベースに設定ファイルを作成：

```yaml
project:
  work_dir: /work/processing/run    # 作業フォルダ
  out_dir:  /work/processing/out    # 出力フォルダ

data:
  slc_dir:   /work/data/sentinel_images     # SLC (SAFE/zip)
  orbit_dir: /work/data/orbits              # 精密軌道
  aux_dir:   /work/data/aux                 # AUX_EAP等
  dem:       /work/data/dem/dem.wgs84       # DEM

aoi:
  swath_num: "2"                            # サブスワス番号
  
coreg:
  method: NESD                              # 共役登録手法
  reference_date: "20200302"                # 主画像日付
  
ifgram:
  workflow: interferogram                   # ワークフロー
  num_connections: 2                        # ネットワーク接続数
  looks:
    range: 9                                # レンジルック数
    azimuth: 3                              # アジマスルック数
    
unwrap:
  method: snaphu                            # アンラッピング手法
```

### Step 3: 処理スクリプト生成・実行

```bash
# スクリプト生成
python tools/gen_stack_scripts.py --config config_your_area.yaml

# 実行
./run_stack.sh

# または、ログ付き実行
./run_all_runs.sh
```

### Step 4: 結果の確認・可視化

```python
# 可視化ツール例
from tools.plot_ts import plot_time_series
from tools.make_ts_gif import create_gif

# 時系列プロット  
plot_time_series('timeseries.h5')

# GIFアニメーション作成
create_gif('timeseries.h5', 'output.gif')
```

## 📁 プロジェクト構造

```
time_series_insar/
├── .devcontainer/           # Dev Container設定
│   ├── devcontainer.json    # VS Code設定
│   ├── docker-compose.yml   # Docker compose設定  
│   ├── Dockerfile           # Docker image定義
│   └── init.sh              # 初期化スクリプト
├── workdir/                 # 作業ディレクトリ
│   ├── notebooks/           # Jupyter notebooks
│   ├── tools/               # 処理ツール
│   └── config_*.yaml        # 設定ファイル例
└── README.md               # このファイル
```

## 🔧 主要ツール

| ツール | 機能 |
|--------|------|
| `download_sentinel.py` | Sentinel-1データのダウンロード |
| `gen_stack_scripts.py` | ISCE2処理スクリプトの生成 |
| `plot_ts.py` | 時系列結果の可視化 |
| `make_ts_gif.py` | アニメーションGIF作成 |
| `tsview_cli.py` | CLI時系列ビューア |

## 📋 設定ファイル詳細

### プロジェクト設定
- `work_dir`: ISCE2の作業ディレクトリ
- `out_dir`: 最終結果の出力先

### データ設定  
- `slc_dir`: Sentinel-1 SLCデータ（SAFEファイル）
- `orbit_dir`: 精密軌道ファイル
- `aux_dir`: 補助データ（AUX_EAP等）
- `dem`: 標高データ（WGS84）

### AOI（解析対象領域）設定
- `swath_num`: サブスワス番号（1, 2, 3 または組み合わせ）
- `bbox_snwe`: 境界ボックス [South, North, West, East]

### 共役登録設定
- `method`: 共役登録手法（NESD, PS等）  
- `reference_date`: 主画像日付
- `esd_coh_threshold`: ESDBurst間コヒーレンス閾値

### 干渉画像設定
- `workflow`: ワークフロー（interferogram, offset等）
- `num_connections`: 時間的ベースライン接続数
- `looks`: レンジ・アジマスルック数
- `filter_strength`: フィルタ強度

## 🚨 トラブルシューティング

### 一般的な問題

**1. メモリ不足エラー**
```yaml
compute:
  num_proc: 2  # プロセス数を削減
```

**2. ディスク容量不足**  
- 不要な中間ファイルを削除
- より小さな解析領域を設定

**3. ネットワークエラー（ダウンロード）**
- `.netrc`ファイルの認証情報を確認
- プロキシ設定を確認

**4. ISCE2パスエラー**
```bash
# コンテナ内で確認
echo $ISCE_HOME
echo $PYTHONPATH
which stackSentinel.py
```

### ログの確認

```bash
# 処理ログの確認
tail -f logs/*/run_stack.log

# ISCE2ログの確認  
tail -f workdir/isce.log
```

## 🤝 貢献

Issue報告や改善提案は歓迎します。

## 📄 ライセンス

このプロジェクトは [MIT License](LICENSE) のもとで公開されています。

## 📚 参考資料

- [ISCE2 Documentation](https://github.com/isce-framework/isce2)
- [MintPy Documentation](https://github.com/insarlab/MintPy)
- [Sentinel-1 Data](https://sentinel.esa.int/web/sentinel/missions/sentinel-1)
- [ASF Data Search](https://search.asf.alaska.edu/)

---

## 💡 Tips

- **初回実行時**: スモールエリアでテスト実行を推奨
- **メモリ使用量**: `num_proc`を適切に調整
- **ストレージ**: SSD使用で大幅な高速化が可能
- **バックアップ**: 重要なデータは定期的にバックアップ

---

**問題や質問がありましたら、Issueを作成してください！**
