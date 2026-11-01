# 코어 알고리즘 다각도 평가 — 2026-10-30

대상: `E:/I-mage-not-AI`, HEAD `c3aff01` 및 평가 시점의 미커밋 변경과 새 벤치마크 산출물. Python 3.12.3 / Windows 로컬 환경. 소스 코드를 수정하거나 엔진을 실행하지 않고 정적 검토, 기존 검사 실행, 임시 디렉터리의 반례 재현으로 평가했다. 이 문서는 평가 산출물이다.

## 판정과 채점 기준

**종합 62/100 — 기본 수치 측정에 장점이 있지만 자동 승인에 필요한 판정 신뢰성은 보완이 필요하다.**

이 점수는 제품의 현재 목적(명시된 제약을 결정론적으로 검증하는 도구)에 대한 엔지니어링 평가다. 미적 품질이나 AI 모델의 능력을 평가한 점수가 아니며, 통계적으로 추정한 전체 정확도도 아니다. 각 점수의 가중합은 61.65이며 반올림했다. 재현된 잘못된 PASS와 검증 목적함수 오류를 큰 감점 요인으로 삼았다.

| 평가 관점 | 점수 / 100 | 가중치 | 평가 근거 |
|---|---:|---:|---|
| 기본 측정의 정확성 | 82 | 15% | 알파 가중 중심, 정규화 여백, 정확 팔레트, 연결 성분, ΔE00 등 기본 연산은 합리적. SVG 상위 변환 누락이 존재 |
| 정책과 최종 판정의 신뢰성 | 40 | 20% | 필수 capability 미강제, 겹치는 규칙의 임계값 덮어쓰기, PASS/INCOMPLETE 불일치 재현 |
| 게임 시계열 검사의 완결성 | 55 | 15% | 정상 미분·부모 변환·쿼터니언 처리는 합리적. 빈 트랙/샘플 부족/jerk 단독 요청의 누락 재현 |
| 성능과 규모 확장성 | 75 | 10% | NumPy/SciPy 벡터화, 기본 시계열 선형 처리. 반복 디코딩·전체 배열 중간값·가림의 레이어 제곱 비용은 제한 |
| 재현성과 설명 가능성 | 88 | 10% | 해시, 공식, 임계값, 단위, 버전, coverage를 기록. 고정 환경의 결정적 측정에 적합. 요청 버전/출처 전달에는 결함 |
| 경계조건과 수치 안정성 | 60 | 10% | 경로 containment, 유한값, 시간 순서, 순환 참조 검증은 강점. 파라미터 0과 샘플 부재, 극단 수치 처리가 약함 |
| 구조와 확장성 | 68 | 10% | adapter/registry/policy 계약이 있으나 실제 실행은 큰 분기 함수와 이름 매핑에 집중. 연결 실수가 실제 발생 |
| 검증 범위와 벤치마크 타당성 | 40 | 10% | 합성 탐지 성과는 인정. 대표성은 좁고 수리 보존·리더보드 목적함수에 중대한 오류 존재 |

## 인정할 강점

- 측정과 사용자 임계값을 분리하고, raster gradient의 의미를 임의로 단정하지 않는 설계가 적절하다.
- 이미지 수치 측정에 NumPy/SciPy를 활용한다. ΔE00에는 표준 예제, 대칭성/비음수성, scalar/vector 일치 검사가 있다. 다만 scalar/vector 일치는 두 구현의 공통 오류를 배제하는 독립 정답 검증과는 다르다.
- 해시 고정, 명시적 provenance, 경로 제한, 고유 ID/참조/시간 검증, CLI exit code와 coverage 계약은 좋은 기반이다.
- 문서는 합성 데이터의 성적, 실제 이미지 품질, 제한된 엔진 fixture 증거를 비교적 정확히 구분한다.

## 우선 해결할 재현 문제

### 1. 필수 capability가 없어도 PASS/COMPLETE — P1

`exact_palette_count` YAML 정책에 `requires: [depth_buffer]`를 선언한다. 단색 PNG에서 planner는 `MISSING_CAPABILITY`와 `INCOMPLETE`를 반환하지만 동일 정책을 넘긴 `review()`는 `PASS/COMPLETE`를 반환한다. 실행이 planner의 capability 판정을 강제하지 않는다.

추가로 algorithm version `99.0`을 요청해도 거절하지 않고 등록된 `1.0`을 실행·기록한다. 해시와 고정 환경 자체의 결정성은 있으나, 선언된 실행 계약이 그대로 지켜지지는 않는다.

근거: [core.py:255](E:/I-mage-not-AI/imreview/core.py:255), [core.py:484](E:/I-mage-not-AI/imreview/core.py:484), [core.py:769](E:/I-mage-not-AI/imreview/core.py:769). 기존 [test_cli.py:132](E:/I-mage-not-AI/tests/test_cli.py:132)는 계획의 capability 표시만 검증한다.

### 2. 규칙 순서에 따라 잘못된 PASS/FAIL — P1

두 색인 mask 영역에 `quantized_palette_count` 정책 두 개를 적용했다. 하나는 `feature_id: face`, 최대 1색이고 다른 하나는 `feature_role: shape`, 최대 5색이다. 두 selector는 같은 대상에 매칭되지만 conflict key가 달라 동시에 남는다. 정책이 하나의 properties 값을 순서대로 덮고, 생성된 단일 측정의 threshold만 나중에 바꾼다.

- 엄격한 규칙 → 느슨한 규칙: 엄격한 규칙 결과가 **measured=2, threshold=1, PASS**. 보고서 `PASS/INCOMPLETE`.
- 순서를 반대로: 느슨한 규칙 결과가 **measured=2, threshold=5, FAIL**. 보고서 `FAIL/INCOMPLETE`.

두 경우 모두 다른 규칙은 INCONCLUSIVE가 된다. CLI는 completeness를 확인해 exit 2/1을 반환하므로 첫 사례가 CLI exit 0을 의미하지는 않는다. 하지만 개별 판정과 최상위 status는 모순된다.

근거: [policies.py:68](E:/I-mage-not-AI/imreview/policies.py:68), [policies.py:113](E:/I-mage-not-AI/imreview/policies.py:113), [core.py:749](E:/I-mage-not-AI/imreview/core.py:749), [core.py:763](E:/I-mage-not-AI/imreview/core.py:763).

### 3. 게임 검사에서 데이터 부재가 PASS — P1

- `samples=[]`인 position 트랙과 `max_position_step=0`: 직접 분석과 manifest review 모두 PASS/COMPLETE. 빈 steps의 최대값을 0으로 바꾼다.
- 2샘플 정지 트랙과 1샘플 트랙에 `max_velocity=0`, `max_position_step=0`: 두 번째 트랙의 속도 검사는 생략되지만 두 경로 모두 PASS. coverage가 대상별 검사 대신 알고리즘 이름의 존재만 확인한다.
- cubic 위치 `[0,1,8,27]`, `max_position_step=100`, `max_jerk=0`: 직접 분석은 jerk를 생성하지 않고 PASS/COMPLETE. jerk 계산이 max_acceleration 조건 내부에 있다. manifest 경로는 jerk 결과 부재를 INCONCLUSIVE로 보완한다.
- 정상 position 트랙과 1샘플 rotation 트랙에서 rotation step/loop를 모두 요구하면 둘 다 PASS 가능. step의 빈 집합을 0으로 처리하고 loop는 생성하지 않는데 같은 알고리즘 이름이 누락을 가린다.

근거: [game.py:404](E:/I-mage-not-AI/imreview/game.py:404), [game.py:410](E:/I-mage-not-AI/imreview/game.py:410), [game.py:419](E:/I-mage-not-AI/imreview/game.py:419), [game.py:439](E:/I-mage-not-AI/imreview/game.py:439), [core.py:469](E:/I-mage-not-AI/imreview/core.py:469).

### 4. SVG 상위 transform을 빠뜨려 길이를 잘못 승인 — P1

`<g transform="scale(100)"><path d="M0 0 L10 0"/></g>`를 `max_path_length=20`으로 검사하면 길이 10, PASS/COMPLETE다. 같은 transform을 path 자체에 넣으면 INCONCLUSIVE다. 현재 지원하지 않는 변환을 보수적으로 보류하는 계약을 조상 변환이 우회한다. 조상 변환을 합성하거나 발견 시 INCONCLUSIVE로 처리해야 한다.

근거: [core.py:325](E:/I-mage-not-AI/imreview/core.py:325), [core.py:534](E:/I-mage-not-AI/imreview/core.py:534).

### 5. 이미지를 투명하게 지워도 수리·보존 100% — P1

생성된 COLOR 결함 이미지에서 RGB를 유지하고 alpha만 전부 0으로 만든 뒤 제출했다. 결과는 `VERIFIED_SYNTHETIC`, `fix_success_rate=1`, `preservation_rate=1`, `changed_pixels=0`, `changes_outside_allowed_region=0`이었다.

원인은 두 가지다. 수리 검사는 가시 색이 0개인 빈 결과도 최대 1색 제약을 통과시키고, 보존 검사는 RGBA 차이를 RGB로 바꿔 alpha 변경을 버린다. 단순 최대 팔레트 측정에서 0이 가능한 것과, 콘텐츠를 보존하는 수리의 성공을 인정하는 것은 구분해야 한다.

근거: [benchmark.py:253](E:/I-mage-not-AI/imreview/benchmark.py:253), [benchmark.py:259](E:/I-mage-not-AI/imreview/benchmark.py:259), [benchmark.py:277](E:/I-mage-not-AI/imreview/benchmark.py:277).

### 6. 고치지 않은 결과가 수리 리더보드에서 우승 — P1

수리 후 잔존 위반을 수리 전 결함 truth와 비교한 F1을 최우선 순위로 사용한다. 동일 COLOR 1케이스에서 그대로 제출하면 F1=1, 수리 성공률=0이고 정상 clean 제출은 F1=null, 수리 성공률=1이다. 순위는 unchanged → clean이었다.

탐지는 수리 전 입력에 대한 finding으로 평가하고, 수리는 수리 성공·잔존 위반·보존을 별도로 평가해야 한다.

근거: [benchmark.py:287](E:/I-mage-not-AI/imreview/benchmark.py:287), [benchmark.py:314](E:/I-mage-not-AI/imreview/benchmark.py:314).

### 7. 잘못된 측정 파라미터를 허용 — P2

`luma_bin_width=0`이 정식 0.5 manifest 로드를 통과한다. 3밝기 이미지가 폭 32에서 levels=3/FAIL, 폭 0에서 divide-by-zero warning과 levels=1/PASS로 바뀐다. `min_`/`max_`만 일반 검증하고 나머지 파라미터에는 계산 도메인 검증이 없다.

근거: [core.py:163](E:/I-mage-not-AI/imreview/core.py:163), [core.py:694](E:/I-mage-not-AI/imreview/core.py:694).

### 8. CIEDE2000 YAML 정책의 결과 연결 오류 — P2

정책 adapter는 SOLID-001에서 결과를 찾지만 실제 CIEDE2000 측정은 SOLID-002를 생성한다. 정상 균일색에서도 실제 측정 PASS와 별도 정책 INCONCLUSIVE가 함께 나오며 최상위는 PASS/INCOMPLETE다.

근거: [policies.py:84](E:/I-mage-not-AI/imreview/policies.py:84), [core.py:643](E:/I-mage-not-AI/imreview/core.py:643).

## 구현 오류와 구분해야 하는 측정 범위

- FFT는 mask 내부 픽셀만이 아니라 mask의 bounding box 전체를 분석한다. 네 모서리만 포함한 mask의 내부를 고정해도 외부 줄무늬 때문에 비율이 0 → 약 0.996으로 바뀐다. 결과 공식에 bbox 방식이 명시되어 있으므로 지원 범위의 한계로 분류했다. 불규칙 mask에서 주의해야 한다. [core.py:710](E:/I-mage-not-AI/imreview/core.py:710)
- 타일 경계는 RGB 차이만 측정한다. alpha 경계, 실제 합성 배경, 미분 연속성을 보증하지 않는다. alpha만 다른 양끝도 error=0이다. [core.py:675](E:/I-mage-not-AI/imreview/core.py:675)
- symmetry는 캔버스 중심 반사이며 silhouette/connectivity는 제공된 mask의 성질이다. 의미적으로 올바른 객체 mask인지 검증하지 않는다.
- exact palette는 JPEG/안티앨리어싱에서 색 수가 쉽게 늘어난다. 고정 Lab bin은 결정적이나 bin 경계에 민감하며 입력 색공간 처리 범위도 제한적이다.
- 극단 쿼터니언 `[1e308,0,0,0]`의 자기 비교는 norm overflow로 360°가 됐다. 정상 q/-q는 0°, 직교 쿼터니언은 180°였다. 유한 입력만 확인하는 것으로 모든 중간 계산의 수치 안정성이 보장되지는 않는다. [game.py:345](E:/I-mage-not-AI/imreview/game.py:345)
- 엔진 exporter는 주로 키 시각을 추출한다. 키 사이 overshoot나 순간 속도, 실제 runtime callback/particle 결과를 일반적으로 보증하지 않는다. 이번 평가는 엔진 실행을 하지 않았으며 기존 fixture 문서의 성공을 새 검증으로 취급하지 않았다.

## 벤치마크와 성능 증거

기존 새 탐지 산출물의 결과는 **40장, 80 규칙 판정, TP20/FP0/FN0/TN60, F1=1.0**이다. 평가 대상은 32×32 합성 아이콘의 팔레트·여백 두 결함이다. clean 대조군과 COMPLETE 확인은 좋은 구성이다. 이는 위 수리 채점 문제와 별도이며 탐지 성과 자체를 부정할 이유는 없다. 다만 실물 이미지, 문자·복잡 SVG·애니메이션·색공간·경계 임계값에 대한 전체 성능으로 일반화할 수 없다. 120회 호출은 반복 측정이며 120개의 독립 이미지가 아니다.

출처: [score.json](E:/I-mage-not-AI/benchmarks/results/icon-v0.2.0/score.json), [run-metadata.json](E:/I-mage-not-AI/benchmarks/results/icon-v0.2.0/run-metadata.json). 이 데이터셋/결과/runner는 평가 시작 시 untracked였다. 이번에 탐지 120회를 다시 실행한 것은 아니다.

이번 `benchmark_review.py 1024 3` 실측은 6.834 / 7.785 / 5.490초, 중앙값 **6.834초**, 8/8 PASS/COMPLETE다. pytest와 같은 호스트에서 일부 동시 실행되었으므로 부하가 통제된 비교 실험이 아니다. 과거 문서의 2.767초와 직접 비교해 회귀라고 판단하지 않았다. 작은 합성 입력의 in-process CLI 시간은 Python 시작 시간이 제외된 다른 지표다.

게임 위치·속도·가속도·jerk 한 트랙의 표적 측정은 1k/10k/50k 샘플에서 약 0.048/0.328/1.272초였다. 모델 검증 시간은 별도이며 단일 로컬 실행이다. 일반 시계열은 선형에 가까우나, alpha 가림은 `O(픽셀 × 레이어²)` 구조다. 이미지마다 반복 decode, feature별 전체 mask 스캔, exact palette 정렬, ΔE00 float64 중간 배열 때문에 대형 이미지/다수 feature에 대한 메모리·성능 검증이 더 필요하다. [game.py:555](E:/I-mage-not-AI/imreview/game.py:555)

## 검증 기록

- `ruff check imreview tests benchmarks`: 통과.
- `mypy imreview tests benchmarks`: 실패. `game.py:260,272,277,280,283`에서 총 8개 타입 오류. 모두 현재 추가된 runtime evidence 분석 부분이다. 타입 오류를 알고리즘 오판으로 동일시하지 않았지만, 문서의 과거 통과 기록은 현재 상태를 대변하지 않는다.
- `.venv/Scripts/python.exe -m pytest -q`: **48 passed**, 267.42초. 기존 테스트 전체가 통과했지만 위 표적 반례는 현재 테스트가 충분히 막지 못하는 경계다.
- 표적 반례는 임시 이미지/manifest/trace/제출 파일로 실행했다. 엔진 실행·빌드·자산 수정은 하지 않았다.

## 권장 개선 순서

1. 규칙 × 대상 × 측정 항목별 필수 결과를 만들고, 증거 부재/샘플 부족/미지원 capability를 INCONCLUSIVE로 통일한다. 모든 결과와 coverage가 확정된 뒤 최상위 status를 한 번 계산한다.
2. 측정값을 공유하더라도 각 정책 assertion은 독립 평가한다. 겹치는 selector의 충돌과 우선순위를 검증하고 요청 algorithm version을 확인한다.
3. 빈 트랙, 부족한 미분 샘플, jerk 단독 요청, 회전 step/loop를 경계 회귀 테스트에 추가한다. SVG는 조상 변환을 합성하거나 보류한다. 모든 측정 파라미터의 도메인을 검증한다.
4. 수리 평가에서 RGBA 네 채널과 필수 콘텐츠 보존을 확인하고 탐지와 수리의 목적함수를 분리한다. 기존 탐지 성적은 유지하되 수리 순위는 수정 후 재계산한다.
5. 이후 실제 이미지·복잡 mask·SVG transform 계층·혼합 키 시각·임계값 근처·큰 입력을 추가한다. ΔE00 외부 정답 벡터 확대, 수치 안정성, peak memory 및 레이어 규모 실측을 보강한다.

현재 활용 판단: 측정값과 근거를 사람이 함께 확인하는 보조 검사에는 유용하다. 자동 승인/품질 게이트 또는 수리 도구 비교의 최종 판정에는 위 P1 문제를 우선 해결해야 한다.

## 후속 수정 기록

2026-10-30 후속으로 발견된 실제 오판과 채점 오류를 보완했다.

- Project rule 매칭은 서로 다른 selector가 실제로 같은 feature/algorithm에 적용될 때 최고 priority 하나를 선택한다. 동률 priority의 상충 기준은 거절하고, 동일 조건의 동률은 규칙 ID로 안정적으로 결정한다. 실행 전 capability/data/version 계획을 enforcement하며 unsupported 측정을 INCONCLUSIVE/SKIPPED로 남긴다. 최상위 status는 결과 적용과 coverage 계산 후 결정한다. CIEDE2000의 rule ID 연결을 SOLID-002로 수정하고 `1`/`1.0` 버전 표기를 동등하게 처리한다.
- 게임 position, rotation, pose, loop, anchor 검사는 데이터가 없거나 샘플이 모자라면 0으로 PASS하지 않고 개별 INCONCLUSIVE 결과를 반환한다. 가속도와 jerk 계산의 의존성을 분리해 jerk 단독 요청도 실제 검사한다.
- SVG 경로에 적용되는 조상 `transform`도 탐지해 변환 좌표를 계산하지 못하는 경로를 INCONCLUSIVE 처리한다. `luma_bin_width`는 유한한 양수만 허용한다.
- 합성 수리 점수는 빈/투명 결과를 팔레트 수정 성공으로 보지 않는다. 보존 검사는 RGBA 네 채널을 비교하고, 잔존 위반 수를 기록한다. 수리 리더보드는 F1보다 잔존 위반 수, 수리 성공률, 보존율을 기준으로 순위화한다. 예전 형식의 잔존 위반 계측이 없는 leaderboard는 잘못 정렬하는 대신 새 leaderboard를 요구한다. 파일형 scoring도 prediction ID 충돌과 FAIL/PASS 중복을 거절한다.
- 회귀 검증 추가: capability 누락 및 버전 불일치, 겹치는 selector와 priority/order, CIEDE2000 정책, 비정상 luminance 폭, SVG ancestor transform, 빈/짧은 game tracks, jerk/rotation sample requirements, alpha 삭제, leaderboard repair priority, prediction dataset identity와 중복 finding.

수정 후 검증은 checkout 그대로 실행했다: `pytest -q` **57 passed**; Ruff 통과. `mypy`는 `imreview`, `tests`, `i_mage_not_ai`, `benchmarks/benchmark_review.py`, `benchmarks/run_icon_dataset.py`의 21개 파일에서 통과했다. 전체 `mypy imreview tests benchmarks i_mage_not_ai`는 새로 추가된 별도 `benchmarks/run_icon_ab_loop.py`에서 10개 typing 오류를 보고해 실패했다. 이 스크립트는 이번 판정/측정 수정 범위와 별개의 untracked 파일이며 변경하지 않았다. `python -m i_mage_not_ai --help`도 checkout에서 성공했다. 기존 `imreview/__main__.py` 삭제와 새 패키지 진입점은 사용자 작업으로 보여 그대로 보존했다.

## 추가 경계 오류 수정 기록

후속 검토에서 위의 범위 제한으로 적어 둔 두 항목도 자동 판정에 영향을 주는 오류로 확인해 수정했다.

- 쿼터니언 거리 계산은 제곱 norm 전에 각 입력을 최댓값으로 나눠 `[1e308,0,0,0]` 자기 비교도 0°로 안정적으로 계산한다.
- seamless tile 경계는 기존 RGB 비교에서 RGBA 비교로 확장해 색은 같고 alpha만 다른 맞닿은 가장자리도 검출한다.
- 각각 대형 유한 쿼터니언 자기 비교와 alpha-only 타일 이음새 회귀 테스트를 추가했다. 최종 checkout 검증: `pytest -q` **59 passed**, Ruff 통과.

상단의 62/100 및 최초 검증 기록은 수정 전 평가 스냅샷 점수/기록이다. 수정 후 새 점수를 산정하지 않았으므로 현재 점수로 해석하면 안 된다.

## 정적 검사 기록 정정

후속 전체 정적 검사에서 보고서에 별도 범위로 남겼던 `benchmarks/run_icon_ab_loop.py`의 타입 오류 10건도 정리했다. 색상 목록 반환형과 픽셀 접근의 타입을 명시하고 전체 검사 명령을 다시 실행한 결과, `mypy imreview tests benchmarks i_mage_not_ai` **22개 파일 통과**, Ruff 전체 통과, `git diff --check` 통과다. 따라서 앞의 “전체 mypy 실패” 기록은 이 정정으로 대체한다.
