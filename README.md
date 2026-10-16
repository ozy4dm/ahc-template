# AHC workspace template

AHC の各回で使う実験記録と比較ツールの雛形です。AHC072 で使用した実験記録、結果一覧、スコアボード、ケース比較の仕組みから、問題に依存しない部分を取り出しました。解法、入力、公式テスタは含めていません。

## 新しい大会での準備

1. このリポジトリを大会用フォルダへ複製します。
2. `AGENTS.md` を開催時点の公式な生成 AI 利用ルールと照合し、必要なら全文を更新します。現行ファイルは暫定版です。
   Claude Code では `CLAUDE.md` が `AGENTS.md` を読み込みます。新しいルールに変わった場合、正本の `AGENTS.md` と Claude 用スキル・プロンプトの整合性を確認してください。
3. `tools/` にその大会の公式 generator / tester / visualizer を配置します。公式配布物のライセンスと公開条件を確認してください。
4. `config.example.json` を `config.json` にコピーし、入力、スコアの向き、ソルバーと採点コマンドを設定します。Windows では実行ファイル名に `.exe` を付けます。
5. 入力を `cases/` の該当する集合へ置き、`docs/experiments/TEMPLATE.md` を複製して評価条件を先に記録します。

`config.json` は大会ごとのローカル設定なので Git の管理対象から外しています。公開時は大会固有の入力、出力、ログ、解法を含めるか個別に確認してください。

## 比較実行

`config.json` の `solvers` と `scorer` はコマンドを文字列配列で指定します。ソルバーは入力を標準入力で受け取り、出力を標準出力へ書きます。採点コマンドの `{input}` と `{output}` はファイルパスに置換され、`score_pattern` の最初の括弧グループから数値を読み取ります。コマンドはシェルを通さず実行されます。

```text
python tools/compare_solvers.py EXP-001 baseline candidate
python tools/show_scoreboard.py --direction lower
powershell -NoProfile -ExecutionPolicy Bypass -File tools/show_experiment_results.ps1
```

比較結果は `reports/experiments/EXP-xxx/` に保存されます。同じ ID の結果は上書きしません。`show_scoreboard.py` は全ケースが揃った版だけを順位表へ載せます。比較や順位表は機械的な集計のみ行い、採用判断は行いません。

## 構成

| パス | 用途 |
|---|---|
| `cases/smoke/` | 入出力と不変条件の確認 |
| `cases/dev/` | 開発中の繰り返し評価 |
| `cases/validation/` | 事前に固定した検証集合 |
| `cases/regression/` | 過去に問題が出たケース |
| `docs/experiments/` | 実験計画と記録 |
| `docs/solutions.md` | 解法版の台帳 |
| `reports/experiments/` | 実行結果 |
| `src/bin/` | 大会ごとの解答コード |
| `tools/` | 比較・集計ツールと大会固有ツール |

AHC072 固有の解法、公式ツール、生成入力、診断用スクリプトは移していません。特に採点式、時間制限、スコアの向きは大会ごとに設定してください。

## Claude Code で使う

リポジトリのルートで Claude Code を起動します。`CLAUDE.md` に共通の作業指示があり、ルール全文は `@AGENTS.md` で読み込まれます。起動後に `/context` で読み込みを確認してください。`.claude/skills/` には `/ahc-setup`、`/ahc-implement`、`/ahc-experiment` の手動スキルを用意しています。記入例は [prompts/README.md](prompts/README.md) にあります。
