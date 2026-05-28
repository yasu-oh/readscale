# ReadScale

**ReadScale** は、チラシ・スライド・スクリーンショット・資料画像など、文字を含む画像を読みやすく拡大するための小さな画像アップスケールツールです。

画像を倍率指定で拡大しつつ、文字・罫線・アイコンなどの輪郭を補正して、可読性を向上させます。

## 特長

- デフォルトで画像を3倍に拡大
- フォルダ一括処理に対応
- 出力ファイル名を省略可能
- 出力ファイル名を省略した場合は `元ファイル名_readscale.拡張子` で保存
- `--scale` で任意の倍率を指定可能
- チラシ、ポスター、スライド、スクリーンショット、UI画像向け
- 文字背景の分離を高める輝度トーンカーブ
- 小さな文字や罫線を持ち上げる局所コントラスト補正
- 文字や罫線に効きやすいエッジ強調処理
- 軽いコントラスト・色味補正
- PNG / JPEG / WebP / BMP / TIFF 出力に対応
- CLIで簡単に実行可能
- AIモデル不要
- Pillowのみでローカル実行可能

## ReadScale が解決すること

一般的な画像リサイズでは、文字がぼやけたり、逆に画像全体が不自然にシャープになりすぎたりすることがあります。

ReadScale は、特に以下のような画像に向いています。

- 小さな文字を含む画像
- UIスクリーンショット
- アイコン
- 細い罫線
- 表
- チラシ
- プレゼン資料

画像全体を強くシャープ化するのではなく、文字や線のようなエッジ部分を中心に補正することで、自然さを保ちながら可読性を高めます。

## インストール

```bash
pip install pillow
```

リポジトリを取得します。

```bash
git clone https://github.com/yasu-oh/readscale.git
cd readscale
```

## 使い方

### 単一ファイルの処理
出力ファイル名を省略できます。

```bash
python readscale.py input.png
```

この場合、入力ファイルと同じディレクトリに `input_readscale.png` として保存されます。

出力ファイル名を明示することもできます。

```bash
python readscale.py input.png output.png
```

### フォルダ一括処理
フォルダを指定することで、中の対応画像をすべて処理できます。

```bash
python readscale.py input_folder/
```

この場合、`input_folder_readscale/` というフォルダが作成され、その中に処理済み画像が保存されます。

出力先フォルダを明示的に指定することも可能です。

```bash
python readscale.py input_folder/ output_results/
```

デフォルトでは、元画像を **3倍** に拡大します。
例: `1000 x 1413 px → 3000 x 4239 px`

## 出力ファイル名

- **ファイル指定時**: 省略時は `元ファイル名_readscale.拡張子` となります。
- **フォルダ指定時**: 省略時は `元フォルダ名_readscale/` となります。

## 倍率指定

`--scale` で拡大倍率を指定できます。

### 4倍に拡大
```bash
python readscale.py input.png --scale 4
```

### 小数倍率も指定できます
```bash
python readscale.py input.png --scale 1.5
```

## 使用例

### 基本的なアップスケール
```bash
python readscale.py input.png
```

### 小さい文字をより強めに補正
```bash
python readscale.py input.png --preset text
```

### 写真が多い画像向けに自然に補正
```bash
python readscale.py input.png --preset soft
```

### ノイズ感を少し抑えて補正
```bash
python readscale.py input.png --preset clean
```

### 自動コントラスト補正を無効化
```bash
python readscale.py input.png --no-autocontrast
```

### 輝度トーンカーブを無効化
```bash
python readscale.py input.png --no-tone-curve
```

### 局所コントラスト補正を無効化
```bash
python readscale.py input.png --no-local-contrast
```

### エッジ強調を無効化
```bash
python readscale.py input.png --no-edge-sharpen
```

### JPEG / WebP の品質を指定
```bash
python readscale.py input.jpg --quality 95
```

### リサイズ方式を指定
```bash
python readscale.py input.png --resample bicubic
```

### DPIメタデータを引き継がない
```bash
python readscale.py input.png --no-keep-dpi
```

## プリセット

| プリセット | 説明 |
| :--- | :--- |
| `flyer` | チラシ、ポスター、スライド向けの標準設定 |
| `text` | 小さい文字や文書画像向けの強めの補正 |
| `soft` | 写真やイラストが多い画像向けの自然な補正 |
| `clean` | JPEGノイズなどを少し抑えたい場合向け |

デフォルトは `flyer` です。

```bash
python readscale.py input.png --preset flyer
```

## 推奨設定

### チラシ・ポスター向け
```bash
python readscale.py input.png
```

### 小さい文字が多い画像向け
```bash
python readscale.py input.png --preset text
```

### 写真を含む資料向け
```bash
python readscale.py input.png --preset soft
```

### JPEGノイズが気になる画像向け
```bash
python readscale.py input.jpg --preset clean
```

### 大きく印刷・表示したい場合
```bash
python readscale.py input.png --scale 4
```

## オプション

| オプション | デフォルト | 説明 |
| :--- | :---: | :--- |
| `input` | 必須 | 入力画像ファイルまたはディレクトリ |
| `output` | 省略可 | 出力画像ファイルまたはディレクトリ。省略時は自動生成 |
| `--scale` | `3.0` | 拡大倍率 |
| `--preset` | `flyer` | 補正プリセット |
| `--resample` | `lanczos` | リサイズ方式 |
| `--no-autocontrast` | 無効 | 自動コントラスト補正を無効化 |
| `--no-tone-curve` | 無効 | 文字背景の分離を高める輝度トーンカーブを無効化 |
| `--no-local-contrast` | 無効 | 小さな文字や罫線向けの局所コントラスト補正を無効化 |
| `--no-edge-sharpen` | 無効 | エッジ強調を無効化 |
| `--quality` | `95` | JPEG / WebP の保存品質 |
| `--no-keep-dpi` | 無効 | 入力画像のDPIメタデータを引き継がない |

## リサイズ方式

`--resample` でリサイズ方式を指定できます。

| 方式 | 説明 |
| :--- | :--- |
| `lanczos` | 高品質な標準設定。通常はこれを推奨 |
| `bicubic` | やや柔らかい結果になりやすい |
| `bilinear` | 軽量だが画質は控えめ |
| `nearest` | ドット絵やピクセル画像向け |

通常はデフォルトの `lanczos` のままで問題ありません。

## 処理の流れ

ReadScale は、おおまかに以下の処理を行います。

1. 入力画像を読み込む
2. EXIFの向き情報を補正
3. 指定倍率で画像を拡大
4. 指定された方式で高品質リサイズ
5. 軽い自動コントラスト補正
6. 明るさ・コントラストを微調整
7. 輝度トーンカーブで文字と背景の分離を補正
8. 局所コントラストで小さな文字や罫線を補正
9. 画像からエッジマスクを生成
10. 文字や罫線などのエッジ部分を中心にシャープ化
11. 色味を微調整
12. PNG / JPEG / WebP / BMP / TIFF などで保存

この処理により、画像全体を過度に加工せず、文字や線の読みやすさを改善します。

## 対応形式

入力形式は Pillow が対応している形式に依存します。

よく使う入力形式:
* PNG
* JPEG
* WebP
* BMP
* TIFF

出力形式:
* PNG
* JPEG
* WebP
* BMP
* TIFF

## 制限事項

ReadScale は AI 超解像モデルではありません。
リサイズと画像補正によって可読性を改善しますが、元画像に存在しない細部を完全に復元することはできません。

より良い結果を得るには、以下を推奨します。
* できるだけ高解像度の元画像を使う
* 同じ画像を何度も繰り返しアップスケールしない
* まずは `flyer` を使い、文字が読みにくい場合だけ `text` を試す
* 写真が多い場合は `soft` を試す
* JPEGノイズが気になる場合は `clean` を試す
* 倍率を上げすぎるとファイルサイズが大きくなるため、用途に応じて `--scale 2` 〜 `--scale 4` 程度を使い分ける

## ライセンス

MIT License
