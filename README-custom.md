# オリジナルに修正した内容
主な変更点は次の通りです。

- オリジナルは`client=vllm`の要件が厳しく、手元のmacOS環境では動かせなかったため、OpenAI互換APIを使ったHTTPアクセス(`client=openai`)を利用する形にした
  - 若干`client=vllm`よりもオーバーヘッドがある
- OllamaのOpenAI互換APIだけをつかって評価するようにコードを修正
- `requrements-ollama.txt`を追加

## 修正したコードと修正内容

### `remote.py`の修正
外部にアクセスしないように必要ない部分のコードを修正。

```sh
% vi src/llm_jp_judge/client/remote.py

//以下の行をコメントアウト
from .local import BaseClient

//以下の行を次のように変更
class OpenAI(BaseClient):
↓
class OpenAI:

//class OpenAIにロジックを追加
class OpenAI:
..
    def get_messages(self, prompt, response, system_prompt=None):
        messages = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        for turn in range(len(prompt)):
            messages.append({"role": "user", "content": prompt[turn]})
            if turn < len(response):
                messages.append({"role": "assistant", "content": response[turn]})
        return messages

    def fill_sampling_params(self, sampling_params):
        return {k: v for k, v in sampling_params.items() if v is not None}
```


### `__init__.py`の上書き
`from .local import vLLMClient`を取り除くなど。

```sh
% vi src/llm_jp_judge/client/__init__.py
from .remote import OpenAI, AzureOpenAI, BedrockAnthropic

def load_client(name="azure", **kwargs):
    if name == "openai":
        return OpenAI(**kwargs)
    elif name == "azure":
        return AzureOpenAI(**kwargs)
    elif name == "bedrock":
        return BedrockAnthropic(**kwargs)
    elif name == "vllm":
        raise RuntimeError(
            "vLLM client is disabled in this macOS/Ollama environment. "
            "Use client=openai with OPENAI_BASE_URL instead."
        )
    raise ValueError(f"Invalid client name: {name}")
```

### `requrements.txt`の修正
一部導入済みだと別のモジュールを使ってサーバーにアクセスしてしまうので、必要なモジュールだけにする。

```text
hydra-core==1.3.2
openai==1.65.2
python-dotenv==1.0.1
anthropic==0.49.0
wandb==0.26.1
```

## 実行方法

### 必要な環境

- コード生成する環境
  - 性能をはかりたいモデルを事前にダウンロードしておく
  - コード生成を比較対象のモデルを使って実施
- 生成されたコードを評価する環境
  - こっちの処理が重いので、32GB以上のメモリーを実装するGPUノード+vLLMなどで可能な限り良いモデルを使って評価を実施
  - 生成されたコードに対して、各種30から50個くらいチェックが行われる
  - 例ではNVIDIA V100環境でQwen2.5-Coder-14Bモデルを使ってコード評価をしている

### 環境の準備
macOSとuvを使うのを前提とした手順で書いています。他の環境では良い感じに置換えてください。
実行前にOllamaの起動と、利用するモデルのpullを実行してください。

Ollama上に比較するモデルをダウンロード。

```sh
% ollama pull gemma4:e2b
% ollama pull gemma4:e4b
```

環境周りの設定。

```sh
# Python 3.9から3.12の間のバージョンを準備
% brew install uv python@3.12

# 前の修正を行ったこのリポジトリーをcloneするか
% git clone https://github.com/ytooyama/llm-jp-judge.git
# オリジナルコードをCloneして上記を修正
# git clone https://github.com/llm-jp/llm-jp-judge.git

# Python仮想環境の作成
% cd llm-jp-judge
% uv venv --python python3.12
% source .venv/bin/activate
% uv pip install -U pip
% uv pip install -r requrements-ollama.txt
```

### テストの実行

#### ケースAのテストを実施

```sh
# OllamaのOPENAI互換APIのアドレスを指定
% export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
% export OPENAI_API_BASE=http://127.0.0.1:11434/v1
% export OPENAI_API_KEY=dummy

# Case Aのテストケース生成の実施
% python3 -m src.llm_jp_judge.generate output.dir=./output/gemma4-e2b/generation client=openai client.model_name=gemma4:e2b benchmark.mt_bench.dataset.path=null

% mkdir -p ./output/gemma4-e2b/generation-ja-only
% cp ./output/gemma4-e2b/generation/ja_mt_bench.jsonl ./output/gemma4-e2b/generation-ja-only/
% cp ./output/gemma4-e2b/generation/metadata.json ./output/gemma4-e2b/generation-ja-only/

# Case Aで生成されたコードの評価
#
# 評価用に、GPUマシマシな別のマシンで動いているLLMを指定
% export OPENAI_API_BASE=http://192.168.1.100:8080/v1
% export OPENAI_BASE_URL=http://192.168.1.100:8080/v1
% export OPENAI_API_KEY=dummy
# 評価
% python3 -m src.llm_jp_judge.evaluate input.dir=./output/gemma4-e2b/generation-ja-only output.dir=./output/gemma4-e2b/evaluation-ja-only client=openai client.model_name=Qwen/Qwen2.5-Coder-14B-Instruct-GPTQ-Int4
```

#### ケースBのテストを実施

```sh 
# OllamaのOPENAI互換APIのアドレスを指定
% export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
% export OPENAI_API_BASE=http://127.0.0.1:11434/v1
% export OPENAI_API_KEY=dummy

# Case Bのテストケース生成の実施
% python3 -m src.llm_jp_judge.generate output.dir=./output/gemma4-e4b/generation client=openai client.model_name=gemma4:e4b benchmark.mt_bench.dataset.path=null

% mkdir -p ./output/gemma4-e4b/generation-ja-only
% cp ./output/gemma4-e4b/generation/ja_mt_bench.jsonl ./output/gemma4-e4b/generation-ja-only/
% cp ./output/gemma4-e2b/generation/metadata.json ./output/gemma4-e4b/generation-ja-only/

# Case Bで生成されたコードの評価
#
# 評価用に、GPUマシマシな別のマシンで動いているLLMを指定
% export OPENAI_API_BASE=http://192.168.1.100:8080/v1
% export OPENAI_BASE_URL=http://192.168.1.100:8080/v1
% export OPENAI_API_KEY=dummy
# 評価
% python3 -m src.llm_jp_judge.evaluate input.dir=./output/gemma4-e4b/generation-ja-only output.dir=./output/gemma4-e4b/evaluation-ja-only client=openai client.model_name=Qwen/Qwen2.5-Coder-14B-Instruct-GPTQ-Int4
```

## Frequently Asked Questions

### mt_benchとja_mt_benchの違い
英語の各能力と日本語の各能力をベンチマークする。細かいパラメータ(`python3 -m src.llm_jp_judge.generate`で`benchmark.mt_bench.dataset.path=null`オプション)を投入しない場合、両方のベンチマークが行われる。

### "No score found in the response. Retrying in 0.5 seconds."と言うメッセージがでる
リトライするから待ちます。評価にはできる限り賢いモデルを使ったほうが良いみたいです。賢いモデルはハードウェアリソースが少ない環境では動かすのが難しいのが悩みどころです。
あまりにも何度もリトライが発生する場合は、評価用としてそのモデルと環境は適切ではありませんので、違う環境を用意することを薦めます。

### このベンチマークで何を行っているか？
llm-jp-judgeでチェックする内容は、以下の通りみたいです。10点満点で何点かを`src.llm_jp_judge.evaluate`の実行時に最終的に出力します。6点以上とれていれば、一般的なタスクは処理できると思われます。

|   タスク   |                            内容                            |
| ---------- | ---------------------------------------------------------- |
| coding     | コード生成・修正・デバッグ                                 |
| extraction | 情報抽出・要約。文章から情報を抜き出す能力                 |
| humanities | 人文系知識・説明能力。歴史、哲学、文化、社会に関する知識力 |
| math       | 数学の文章題、数式推論、途中説明についての能力             |
| reasoning  | 論理推論、条件整理、因果関係、多段推論能力                 |
| roleplay   | キャラクター応答・会話。人格模倣してタスクを処理する能力   |
| stem       | 科学技術一般。科学、工学、IT系、物理に関する能力           |
| writing    | 記事作成、メール文章作成、説明文、文章の創作能力           |