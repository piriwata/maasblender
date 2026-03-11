# routedeviation シミュレータ

## 概要

`routedeviation` は、**定路線型デマンドレスポンシブトランスポート (DRT)** をシミュレートするモジュールです。車両は基本的に固定の時刻表に沿った路線を走行しますが、事前に指定された**柔軟区間（経路逸脱可能区間）**内では、利用者の予約状況に応じて経路を逸脱し、任意の地点で乗降できます。

本シミュレータは [GTFS-Flex](https://gtfs.org/extensions/flex/) の `location_id` による柔軟な乗降地点の表現に対応しており、MaaS Blender プラットフォームの REST API を介して他のコンポーネントと連携します。

## ディレクトリ構成

```
routedeviation/
├── main.py          # エントリポイント（uvicorn 起動）
├── controller.py    # REST API エンドポイント（FastAPI）
├── simulation.py    # シミュレーション全体の統括
├── mobility.py      # 車両（Car）とその管理（CarManager）
├── trip.py          # 経路・停車情報と経路逸脱アルゴリズム
├── core.py          # ドメインモデル（Stop, User, Path, Service 等）
├── gtfs.py          # GTFS ファイルのパーサー
├── event.py         # イベント定義とイベントキュー
├── environment.py   # SimPy の環境ラッパー
├── jschema/
│   ├── query.py     # リクエストスキーマ（Pydantic）
│   └── response.py  # レスポンススキーマ（Pydantic）
├── test/
│   ├── test_internal.py  # 統合テスト
│   └── test_service.py   # Service クラスのユニットテスト
└── requirements.txt
```

## アーキテクチャ

```
外部クライアント（Simulation Broker）
        │
        │  REST API (HTTP)
        ▼
┌──────────────────┐
│  controller.py   │  FastAPI アプリケーション
└────────┬─────────┘
         │
         ▼
┌──────────────────┐      ┌───────────────┐
│  simulation.py   │─────▶│   gtfs.py     │ GTFS ファイルの解析
│  (Simulation)    │      └───────────────┘
└────────┬─────────┘
         │
         ├──────────────────────────────────────────┐
         ▼                                          ▼
┌──────────────────┐                    ┌──────────────────────┐
│  mobility.py     │                    │  event.py            │
│  (CarManager,Car)│                    │  (EventQueue)        │
└────────┬─────────┘                    └──────────────────────┘
         │
         ▼
┌──────────────────┐      ┌───────────────────────┐
│  trip.py         │─────▶│  core.py              │
│  (SingleTrip,    │      │  (Stop, User, Path 等) │
│   BlockTrip)     │      └───────────────────────┘
└──────────────────┘
         │
         ▼
┌──────────────────┐
│  environment.py  │  SimPy ラッパー（時間管理）
│  (Environment)   │
└──────────────────┘
```

## 各ファイルの詳細

### `main.py`

uvicorn で FastAPI アプリを起動するエントリポイントです。ポート 8002 で起動します。

```python
uvicorn.run("controller:app", port=8002)
```

---

### `controller.py`

FastAPI を用いた REST API の定義ファイルです。以下のエンドポイントを提供します。

| メソッド | パス          | 説明                                           |
|----------|---------------|------------------------------------------------|
| GET      | `/spec`       | イベント仕様の取得                             |
| POST     | `/upload`     | GTFS ファイルのアップロード                    |
| POST     | `/setup`      | シミュレーションの初期化（GTFS 読み込み）      |
| POST     | `/start`      | シミュレーションの開始                         |
| GET      | `/peek`       | 次のイベント発生時刻の取得                     |
| POST     | `/step`       | シミュレーションを 1 ステップ進める            |
| POST     | `/triggered`  | 外部イベント（予約・出発）の受け付け           |
| GET      | `/reservable` | 指定区間が予約可能か確認                       |
| POST     | `/finish`     | シミュレーションの終了・リセット               |

**`/setup` の動作:**

1. GTFS ファイル（ZIP）をダウンロードまたはアップロード済みファイルから取得
2. `GtfsFilesReader` でパース
3. `Simulation` インスタンスを生成

**`/triggered` の動作:**

`ReserveEvent` または `DepartEvent` を受け取り、それぞれ `simulation.reserve_user()` / `simulation.dept_user()` を呼び出します。

---

### `simulation.py`

シミュレーション全体を統括するクラス `Simulation` を定義します。

#### 主要メソッド

| メソッド | 説明 |
|----------|------|
| `start()` | 全車両のシミュレーションプロセスを開始 |
| `peek()` | 次のイベント発生時刻を返す（SimPy の `peek()`）|
| `step()` | 1 ステップ実行し、現在時刻を返す |
| `reserve_user()` | 利用者を予約する。最も早く目的地に到着できる車両を探して予約 |
| `dept_user()` | 利用者を出発待機状態に移行させる |
| `reservable()` | 指定区間が予約可能か判定する |

#### `_to_stop_like()` メソッド

`location_id` を `Stop`（固定停留所）または `TemporaryStop`（柔軟停留所）に変換します。固定停留所として登録されていない場合は、GTFS の `TripLocation` に対応する `TemporaryStop` を生成します。

---

### `mobility.py`

車両の動作ロジックを担う `Car` クラスと、複数車両を管理する `CarManager` を定義します。

#### `Car` クラス

`Mobility` を継承し、SimPy のプロセスとして非同期に動作します。

**主要プロパティ:**

| プロパティ | 説明 |
|------------|------|
| `reserved_users` | 予約済み利用者（RESERVED 状態）|
| `waiting_users` | 停留所で待機中の利用者（WAITING 状態）|
| `passengers` | 乗車中の利用者（RIDING 状態）|

**`run()` メソッド（SimPy プロセス）:**

時刻表に従って停車駅を順に巡回します：

```
while True:
    trip の各停車地点に対して:
        1. 到着時刻まで待機 (env.timeout_until)
        2. 到着処理 (_arrive): 降車ユーザーを処理、ArrivedEvent を発行
        3. 出発時刻まで待機
        4. 出発処理 (_departure): 乗車ユーザーを処理、DepartedEvent を発行
```

柔軟区間に予約が入っている場合、`trip.iter_stop_times_at()` が経路逸脱後の一時停車地点を返します（後述）。

**`is_reservable()` メソッド:**

新しい予約を加えても座席容量を超えないかチェックします。既存の全予約と新予約のそれぞれの乗車区間を比較し、同時乗車数が容量を超えないことを確認します。

**`earliest_path()` メソッド:**

出発地・目的地・希望出発時刻から、最も早く到達できる経路を探します。前日・当日・翌日の 3 日分を検索します。

#### `CarManager` クラス

複数の `Car` インスタンスを管理し、`earliest_mobility()` で最も早く目的地に到達できる車両を選択します。

---

### `trip.py`

時刻表の管理と**経路逸脱アルゴリズム**の中核を担うファイルです。

#### `SingleTrip` クラス

1 つの運行区間（連続する停車地点の列）を表します。`stop_times_with` は `StopTime`（固定停留所）と `TripLocation`（柔軟区間）が混在するリストです。

例：
```
[StopTime(A, 9:00), TripLocation(X, 9:05~9:15), StopTime(B, 9:20)]
```
これは「A 停留所 → 柔軟区間 X（9:05〜9:15 の間に逸脱可能）→ B 停留所」を意味します。

**`iter_stop_times_at()` メソッド:**

シミュレーション実行時に、各停車地点を順に返すイテレータです。固定停留所はそのまま返し、`TripLocation` は実際の予約状況をもとに経路逸脱後の一時停車地点リストに展開します。

#### `BlockTrip` クラス

同一の `block_id` を持つ複数の `SingleTrip` を連結した運行（例：往復運行）を表します。曜日設定によって一部の `SingleTrip` のみが運行する場合を考慮します。

#### 経路逸脱アルゴリズム（`get_deviated_stops()`）

柔軟区間 `TripLocation` における一時停車地点の訪問時刻を算出します。

**アルゴリズム:**

ある柔軟区間において、前後の固定停留所の出発時刻 `departure` と到着時刻 `arrival` の間に n 件の乗降予約がある場合：

```
時間窓の開始時刻 T1 = departure
時間窓の終了時刻 T2 = arrival
n = 乗降する利用者数
```

各利用者 i（1 ≦ i ≦ n）の訪問時刻：
```
T1 + (i / (n + 1)) × (T2 - T1)
```

これにより、n 件の乗降を `(T2 - T1)` の時間窓内に均等に分散させます。

**例（n=2, T1=9:00, T2=9:12）:**

```
利用者 1 の訪問時刻: 9:00 + (1/3) × 12分 = 9:04
利用者 2 の訪問時刻: 9:00 + (2/3) × 12分 = 9:08
```

実装（`trip.py` L127–133）:
```python
n = len(tstops) + 1
return [
    DeviatedStopTimeWithDateTime(tstop, dt_initial + i / n * duration)
    for i, tstop in enumerate(tstops, 1)
]
```

#### `_get_paths()` 関数

出発地（`org`）と目的地（`dst`）のペアから、有効な乗車経路（`Path`）を列挙します。出発地・目的地がそれぞれ `Stop` か `TemporaryStop` かを判別し、対応する時刻情報を組み合わせます。

---

### `core.py`

シミュレーション全体で使用するドメインモデルを定義します。

#### 主要クラス

| クラス | 説明 |
|--------|------|
| `Stop` | 固定停留所（stop_id, 名前, 緯度, 経度）|
| `TemporaryStop` | 経路逸脱時の一時停車地点（緯度, 経度, TripLocation）|
| `TripLocation` | 柔軟区間の定義（location_id, 時間窓）|
| `StopTime` | 固定停留所の発着時刻 |
| `StopTimeWithDateTime` | 日付を含む発着時刻 |
| `DeviatedStopTimeWithDateTime` | 経路逸脱時の一時停車地点の時刻 |
| `Service` | 運行カレンダー（曜日・日付例外設定）|
| `Path` | 乗車経路（乗車地点・降車地点・出発時刻・到着時刻）|
| `User` | 利用者（RESERVED → WAITING → RIDING の状態遷移）|
| `Mobility` | 車両の抽象基底クラス |

#### `UserStatus` の状態遷移

```
RESERVED  ──(dept_user 呼び出し)──▶  WAITING  ──(車両到着・乗車)──▶  RIDING
```

- **RESERVED**: 予約済み・まだ停留所に向かっていない
- **WAITING**: 停留所で待機中（`dept_user` が呼ばれた後）
- **RIDING**: 車両に乗車中

#### `Service` クラス

GTFS の `calendar.txt` / `calendar_dates.txt` に対応した運行カレンダーです。曜日ごとの運行可否と例外日付（追加・削除）を管理します。

#### `Path` クラス

乗車区間の情報を保持します。`pick_up_stop` / `drop_off_stop` が `None` でない場合、その地点は固定停留所ではなく柔軟区間内の任意地点であることを示します。

---

### `gtfs.py`

GTFS 形式（ZIP ファイル）を読み込み、シミュレーション用のデータ構造に変換するパーサーです。

#### 読み込むファイル

| GTFS ファイル | 生成するオブジェクト |
|----------------|----------------------|
| `agency.txt` | `Agency` |
| `stops.txt` | `Stop` |
| `routes.txt` | `Route` |
| `calendar.txt` | `Service` |
| `calendar_dates.txt` | `Service`（例外日付の追記）|
| `stop_times.txt` | `StopTime` または `TripLocation` |
| `trips.txt` | `SingleTrip` |

#### GTFS-Flex 対応

`stop_times.txt` の各行について：
- `stop_id` がある場合 → `StopTime`（固定停留所）
- `location_id` がある場合 → `TripLocation`（柔軟区間）
- `location_group_id` がある場合 → **非対応**（オンデマンドシミュレータを使用）

#### ブロック運行（`block_id`）

`trips.txt` で `block_id` が設定されている複数の `SingleTrip` は、`blocks` として分類されます。後で `BlockTrip` に結合されます。

---

### `event.py`

シミュレーション中に発生するイベントの定義とキューを管理します。

#### イベントクラス

| クラス | `eventType` | 説明 |
|--------|-------------|------|
| `ReservedEvent` | `RESERVED` | 予約成功イベント |
| `ReserveFailedEvent` | `RESERVED` | 予約失敗イベント（`success: false`）|
| `DepartedEvent` | `DEPARTED` | 車両・利用者の出発イベント |
| `ArrivedEvent` | `ARRIVED` | 車両・利用者の到着イベント |

イベントは `EventQueue` に積まれ、`/step` API のレスポンスとして一括返却されます。

#### イベントの JSON 形式

**予約成功（ReservedEvent）:**
```json
{
  "eventType": "RESERVED",
  "time": 543.0,
  "details": {
    "success": true,
    "userId": "U_001",
    "demandId": "D_0001",
    "mobilityId": "trip_001",
    "route": [{
      "org": {"locationId": "stop_A", "lat": 36.69, "lng": 137.22},
      "dst": {"locationId": "stop_B", "lat": 36.70, "lng": 137.23},
      "dept": 543.0,
      "arrv": 574.0
    }]
  }
}
```

**到着（ArrivedEvent）:**
```json
{
  "eventType": "ARRIVED",
  "time": 574.0,
  "details": {
    "userId": "U_001",
    "demandId": "D_0001",
    "mobilityId": "trip_001",
    "location": {"locationId": "stop_B", "lat": 36.70, "lng": 137.23}
  }
}
```

---

### `environment.py`

SimPy の `Environment` クラスをラップし、シミュレーション時刻（分単位の経過時間）と現実の日時（`datetime`）の相互変換を提供します。

| メソッド | 説明 |
|----------|------|
| `datetime_from(elapsed)` | 経過時間（分）→ `datetime` |
| `elapsed(date_time)` | `datetime` → 経過時間（分）|
| `timeout_until(date_time)` | 指定 `datetime` まで待機する SimPy イベント |

時刻の単位は **分**（minutes）です。

---

## データフロー

### 1. セットアップ

```
POST /upload  ──▶  GTFS ZIP ファイルをサーバーに保存
POST /setup   ──▶  GTFS を解析し、Simulation インスタンスを生成
POST /start   ──▶  全車両の SimPy プロセスを開始
```

### 2. 通常運行ループ

```
GET  /peek    ──▶  次のイベント発生時刻を確認
POST /step    ──▶  シミュレーションを進め、発生したイベントを返す
```

### 3. 利用者の予約・乗車

```
POST /triggered (ReserveEvent)
  ├─▶ simulation.reserve_user()
  ├─▶ CarManager.earliest_mobility()  最適な車両を探す
  ├─▶ Car.is_reservable()             容量チェック
  ├─▶ Car.reserve()                   予約登録
  └─▶ ReservedEvent をキューに追加

POST /triggered (DepartEvent)
  ├─▶ simulation.dept_user()
  └─▶ User の状態を WAITING に変更（停留所で待機開始）
```

### 4. 車両の到着・出発（Car.run() プロセス内）

```
時刻表の各停車地点（固定 + 逸脱地点）に対して:
  1. plan.arrival まで待機
  2. _arrive(stop):
     - ArrivedEvent（車両）を発行
     - 降車対象ユーザーに ArrivedEvent（ユーザー）を発行し、users から削除
  3. plan.departure まで待機
  4. _departure():
     - 乗車対象ユーザーに DepartedEvent（ユーザー）を発行し、ride() を呼ぶ
     - DepartedEvent（車両）を発行
```

---

## GTFS-Flex の利用方法

本シミュレータは GTFS-Flex の柔軟な乗降地点表現を拡張して使用します。`stop_times.txt` に `location_id` を記述することで柔軟区間を定義できます。

**`stop_times.txt` の例:**
```csv
trip_id,arrival_time,departure_time,stop_id,stop_sequence,location_id,start_pickup_drop_off_window,end_pickup_drop_off_window
trip_001,09:00:00,09:00:00,stop_A,1,,,
trip_001,,,,,flex_zone_X,09:05:00,09:15:00
trip_001,09:20:00,09:20:00,stop_B,3,,,
```

これにより、「stop_A → 柔軟区間 flex_zone_X（09:05〜09:15）→ stop_B」という路線が定義されます。利用者が `flex_zone_X` 内の任意地点での乗降を予約すると、車両はその地点に立ち寄ります。

> **注意:** `location_group_id` による on-demand バスサービスは本シミュレータでは非対応です。代わりに `ondemand` シミュレータを使用してください。

---

## テスト

```bash
cd src/base_simulators/routedeviation
python -m pytest test/
```

- `test_service.py`: `Service` クラス（運行カレンダー）のユニットテスト
- `test_internal.py`: `SingleTrip` および `BlockTrip` を用いた統合テスト（富山市のバスデータをベースにした座標を使用）

---

## 他のシミュレータとの違い

| シミュレータ | 乗降地点 | 経路 |
|--------------|----------|------|
| `scheduled` | 固定停留所のみ | 固定時刻表 |
| `routedeviation` | 固定停留所 + 柔軟区間内の任意地点 | 基本は固定時刻表、柔軟区間のみ逸脱可能 |
| `ondemand` | 任意地点（`location_group_id`）| 完全オンデマンド |
| `walking` | 徒歩経路 | 徒歩 |
| `oneway` | 一方向移動 | 固定 |
