# AGENTS_PROJECT.md

このファイルは WanaLyser 固有の AI agent 向け運用メモです。
共通ルールは dotfiles の `templates/AGENTS_BASE.md` に集約します。

## Goal
- 放射線治療装置の Winston-Lutz テスト画像を解析し、照射野中心と球体中心の二次元的なずれを mm 単位で記録する。
- GUI で日常点検と一時的な確認を扱い、解析条件、装置名、点検種別、結果を SQLite に保存できるようにする。
- 施設や撮影手順の差を吸収するため、撮影条件は `setup` と `preset` で管理する。

## Current Implementation
- エントリポイントは `src/main.py`。GUI は PySide6 ベースで、Tkinter からの移行予定ではなく、現行実装として PySide6 を使用している。
- CLI は `src/analyze.py`。画像解析、debug 出力、DB 保存、preset 一覧、plan preview、DB 結果一覧に対応している。
- 解析コアは `src/core.py`。対応拡張子は現状 `.bmp`, `.png`, `.tif`, `.tiff`。DICOM は sample にあるが、正式対応は未定で、現行の `SUPPORTED_IMAGE_EXTENSIONS` には含まれていない。
- DB 周りは `src/database.py`。`machines`, `sessions`, `analysis_results`, `setups`, `setup_presets`, `setup_steps`, `app_settings` を作る。
- 解析 plan は `src/workflow.py`。入力画像順と preset metadata を対応付けて `AnalysisPlanItem` を作る。
- builtin preset は `src/setups.py` の `daily-14`。`sample/set_01` の 14 枚撮影順を前提にしている。
- PDF レポートは `src/report.py`。GUI からも CLI テストからも使われる。

## Domain Context
- 主な入力は放射線治療装置から出力される BMP 画像。DICOM タグに依存した解析は前提にしない。
- 解析は矩形照射野の中心と球体中心を画像上で検出し、pixel size から `dx_mm`, `dy_mm`, `distance_mm`, `angle_degrees` を算出する。
- 日常点検では 14 枚の画像を固定順で撮影する運用があるが、点検や施設差により必要条件は変わり得る。その差は setup/preset を編集して吸収する。
- `sample/size` は解析パラメータ調整とテスト用画像として使う。

## Commands
- `rtk python3 -m unittest discover -s test -p 'test_*.py'`: 標準ライブラリだけで全テストを実行する。
- `rtk python3 -m pytest -q`: pytest が入っている環境での全テスト実行。現環境では pytest 未導入の可能性がある。
- `rtk python3 src/analyze.py --list-presets`: DB 初期化後、登録済み preset を確認する。
- `rtk python3 src/analyze.py sample/set_01 --preset daily-14 --preview-plan`: 画像順と preset の対応を確認する。
- `rtk python3 src/analyze.py sample/size -o log/core_debug`: 解析結果と debug 画像を出力する。
- `rtk python3 src/main.py`: GUI を起動する。表示確認が必要な場合に使う。

## Conventions
- 既存の単純な dataclass と関数分割を優先し、単発用途の抽象化は増やさない。
- 解析のデフォルト値は `src/core.py` の `DEFAULT_*` 定数を使う。別ファイルで `0.242`, `0`, `10` を直接増やさない。
- DB に保存する角度やラベルは `AnalysisMetadata` を経由する。
- preset の返す metadata 数は preset 定義に従う。画像数と合わない場合でも、手動割り当てや部分運用のために即エラーにはしない。
- test 実行でできた cache、log、DB などの生成物は確認なしに削除してよい。ただし git 管理されているファイルは削除前に確認する。

## Risks
- 解析アルゴリズムの閾値や検出候補選択を変えると、既存テスト画像の `dx_mm` / `dy_mm` が変わる。変更時は `test/test_core.py` と sample 画像で確認する。
- setup/preset の順序は日常点検結果の意味に直結する。`daily-14` の順序変更は GUI、CLI、既存データ表示に影響する。
- `metadata_for_preset` は画像数と metadata 数の不一致を許容している。ここを厳密化すると部分的な点検運用を壊す可能性がある。
- `init_db()` は builtin setup/preset を seed する。名前が同じ user setup を上書きする可能性を考えて、seed 処理の変更は慎重に行う。
- GUI は `src/gui.py` が大きい。表示文言や列順を変える場合は、保存、再読込、PDF 出力まで影響を確認する。

## Open Questions
- DICOM 読み込みは未定。現状は sample に `.dcm` があるが、解析対象拡張子には入っていない。
- builtin `daily-14` の角度名と実運用の表記をどこまで標準化するか。
- user が作成した setup/preset と builtin seed の衝突時の扱いを明確にするか。
- GUI の `src/gui.py` をさらに分割する場合、機能単位、タブ単位、DB 操作単位のどれを優先するか。
