# ReadScale

**ReadScale** は、チラシ・スライド・スクリーンショット・資料画像など、文字を含む画像を読みやすく拡大するための小さな画像アップスケールツールです。

画像を倍率指定で拡大しつつ、文字・罫線・アイコンなどの輪郭を補正して、可読性を向上させます。

## 特長

- デフォルトで画像を **3倍** に拡大
- `--scale` で任意の倍率を指定可能
- チラシ、ポスター、スライド、スクリーンショット、UI画像向け
- 輝度成分を中心に補正し、色味の変化を抑制
- 文字・罫線・アイコンなどのエッジを中心にシャープ化
- JPEG由来のノイズや圧縮感を抑える `clean` プリセット
- `lanczos` / `bicubic` / `bilinear` / `nearest` のリサンプリング方式を選択可能
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
- JPEG圧縮済みの告知画像や資料画像

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

```bash
python readscale.py input.png output.png
```

デフォルトでは、元画像を **3倍** に拡大します。

例:

```text
1000 x 1413 px → 3000 x 4239 px
```

## 倍率指定

`--scale` で拡大倍率を指定できます。

### 4倍に拡大

```bash
python readscale.py input.png output.png --scale 4
```

### 小数倍率で拡大

```bash
python readscale.py input.png output.png --scale 1.5
```

## 使用例

### 基本的なアップスケール

```bash
python readscale.py flyer.png flyer_upscaled.png
```

### 小さい文字をより強めに補正

```bash
python readscale.py input.png output.png --preset text
```

### 写真やイラストが多い画像を自然に補正

```bash
python readscale.py input.png output.png --preset soft
```

### JPEG圧縮ノイズが気になる画像を補正

```bash
python readscale.py input.jpg output.png --preset clean
```

### 自動コントラスト補正を無効化

```bash
python readscale.py input.png output.png --no-autocontrast
```

### エッジ強調を無効化

```bash
python readscale.py input.png output.png --no-edge-sharpen
```

### JPEG / WebP の品質を指定

```bash
python readscale.py input.jpg output.jpg --quality 95
```

### リサンプリング方式を指定

```bash
python readscale.py input.png output.png --resample bicubic
```

### DPIメタデータを引き継がない

```bash
python readscale.py input.png output.png --no-keep-dpi
```

## プリセット

| プリセット | 説明 |
|---|---|
| `flyer` | チラシ、ポスター、スライド向けの標準設定 |
| `text` | 小さい文字や文書画像向けの強めの補正 |
| `soft` | 写真やイラストが多い画像向けの自然な補正 |
| `clean` | JPEG圧縮ノイズやざらつきが気になる画像向け |

デフォルトは `flyer` です。

```bash
python readscale.py input.png output.png --preset flyer
```

## リサンプリング方式

| 方式 | 説明 |
|---|---|
| `lanczos` | 高品質な拡大向け。デフォルト |
| `bicubic` | やや柔らかい拡大結果にしたい場合 |
| `bilinear` | 軽量だが、文字入り画像ではやや甘くなりやすい |
| `nearest` | ピクセルアートやドット絵向け。通常のチラシ用途には非推奨 |

デフォルトは `lanczos` です。

```bash
python readscale.py input.png output.png --resample lanczos
```

## 推奨設定

### チラシ・ポスター向け

```bash
python readscale.py input.png output.png
```

### 小さい文字が多い画像向け

```bash
python readscale.py input.png output.png --preset text
```

### 写真を含む資料向け

```bash
python readscale.py input.png output.png --preset soft
```

### JPEG由来のノイズが気になる画像向け

```bash
python readscale.py input.jpg output.png --preset clean
```

### 大きく印刷・表示したい場合

```bash
python readscale.py input.png output.png --scale 4
```

## オプション

| オプション | デフォルト | 説明 |
|---|---:|---|
| `--scale` | `3.0` | 拡大倍率 |
| `--preset` | `flyer` | 補正プリセット。`flyer` / `text` / `soft` / `clean` |
| `--resample` | `lanczos` | リサンプリング方式。`lanczos` / `bicubic` / `bilinear` / `nearest` |
| `--no-autocontrast` | 無効 | 自動コントラスト補正を無効化 |
| `--no-edge-sharpen` | 無効 | エッジ強調を無効化 |
| `--quality` | `95` | JPEG / WebP の保存品質 |
| `--no-keep-dpi` | 無効 | 入力画像のDPIメタデータを引き継がない |

## 処理の流れ

ReadScale は、おおまかに以下の処理を行います。

1. 入力画像を読み込む
2. EXIFの向き情報を補正
3. 画像モードを RGB / RGBA に正規化
4. 指定倍率で画像を拡大
5. 輝度成分を中心に自動コントラスト補正
6. 明るさ・コントラスト・色味を微調整
7. 局所コントラストからエッジマスクを生成
8. 文字や罫線などのエッジ部分を中心にシャープ化
9. 必要に応じてアルファチャンネルを復元
10. PNG / JPEG / WebP / BMP / TIFF などで保存

この処理により、画像全体を過度に加工せず、文字や線の読みやすさを改善します。

## 対応形式

入力形式は Pillow が対応している形式に依存します。

よく使う入力形式:

- PNG
- JPEG
- WebP
- BMP
- TIFF

出力形式:

- PNG
- JPEG
- WebP
- BMP
- TIFF

出力ファイルの拡張子は、以下に対応しています。

```text
.png
.jpg
.jpeg
.webp
.bmp
.tif
.tiff
```

## 制限事項

ReadScale は AI 超解像モデルではありません。

リサイズと画像補正によって可読性を改善しますが、元画像に存在しない細部を完全に復元することはできません。

より良い結果を得るには、以下を推奨します。

- できるだけ高解像度の元画像を使う
- 同じ画像を何度も繰り返しアップスケールしない
- まずは `flyer` を使い、文字が読みにくい場合だけ `text` を試す
- JPEG由来のざらつきや圧縮ノイズが気になる場合は `clean` を試す
- 倍率を上げすぎるとファイルサイズが大きくなるため、用途に応じて `--scale 2` 〜 `--scale 4` 程度を使い分ける

## ライセンス

MIT License
