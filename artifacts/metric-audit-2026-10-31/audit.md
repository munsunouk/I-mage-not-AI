# 평가 지표 자체에 대한 감사 — 2026-10-31

## 판정

**현재 평가를 100점짜리 평가라고 볼 수 없다. 일부 계산식은 독립 정답으로 검증됐지만, 현재 아이콘 A/B 벤치마크에는 정답 누출, 출력과 무관한 마스크 검사, 채점 비대칭이 있다. 일반 이미지 생성 품질·미감·AI slop 판정의 타당성은 검증되지 않았다.**

공인된 종합 점수 척도나 사전 등록된 가중치가 없으므로 62점·80점 같은 임의 총점은 부여하지 않았다. 아래 판정은 실제 반례, 코드, 통계 가정, 외부 평가 연구를 근거로 한다. `F1=100%`는 특정 표본의 관측값이지 평가 방법 자체의 완성도 점수가 아니다.

수학·알고리즘, 실험·통계, 외부 기준 타당성을 3개 AI 에이전트가 분담 검토하고, 주 에이전트가 저장된 사례와 수치를 재현했다. 이는 사람 대상의 블라인드 평가나 독립 연구기관의 인증을 대체하지 않는다. 범위는 현재 이미지/마스크 계산과 `icon-multimetric-isolated-loop-04`이며, 전체 프로젝트에 대한 완전한 코드 감사는 아니다. 과거 2026-10-30 보고서의 62/100은 수정 전 스냅샷이라 이번 점수로 재사용하지 않았다.

| 평가 조건 | 판정 | 확인한 근거 |
|---|---|---|
| 계산식의 수치 정확성 | 일부 검증 통과 | 알려진 값 검사 6개 통과; ΔE00 공식 34개 공개 참조쌍 통과 |
| 실제 제출 이미지에 대한 민감도 | 실패 | 입력과 픽셀이 같은 결과가 정답 마스크 교체만으로 대칭/겹침 PASS |
| 정답과 평가 정책의 독립성 | 실패 | 결함 라벨을 읽어 중심·대칭 임계값을 변경 |
| 동일한 진단 채점 계약 | 실패 | AO 자유문 채점, CLI arm은 raw CLI finding으로 덮어씀; 부정문 오채점 |
| 실제 사용자 품질과의 일치 | 미검증 | 사람 선호·의미 인지·작은 크기 사용성 라벨 없음 |
| 표본 대표성과 불확실성 | 불충분 | 24개 결함 입력이 4개 원본을 반복; 1회 실험 |
| 수정 금지 영역의 보존 | 이번 점수에서 미측정 | 허용 수정 마스크 밖 RGBA 변화에 대한 독립 점수 없음 |
| 재현성 자료 | 부분 충족 | PNG·manifest·SHA·JSON 보존; 모델/토큰/시간/반복 조건 고정 기록은 부족 |

## 1. 고치지 않았는데 해당 출력 검사가 PASS한다 — P1

실제 저장 파일을 RGBA 배열로 비교했다. PNG 파일 바이트는 재인코딩에 따라 달라지므로 픽셀 동일성을 기준으로 삼았다.

| 사례 | AO 입력과 출력의 RGBA | 원래 검사 | 수정 후 검사 |
|---|---|---|---|
| sample-02, 겹침 | 완전히 동일 | overlap=1.0, FAIL | overlap=0.0, PASS |
| sample-09, 대칭 | 완전히 동일 | symmetry=0.0, FAIL | symmetry=1.0, PASS |

[채점기](E:/I-mage-not-AI/benchmarks/score_multimetric_ab.py:160)는 clean renderer에서 특징 마스크를 생성한다. 제출 이미지에서 다시 구하는 것은 실루엣뿐이고 보석·보석쌍 마스크는 정답 좌표다. 대칭 점수는 `|M ∩ flip(M)| / |M ∪ flip(M)|`, 겹침 점수는 `|A ∩ B| / min(|A|, |B|)`이다. 마스크 M,A,B가 고정되면 제출 이미지 I의 내용은 이 두 식에 영향을 주지 않는다.

따라서 기존 **20/24 all-output-checks-pass를 완전한 실제 수정 성공률로 취급하면 안 된다.** 검사는 올바른 산식을 잘못된 측정 입력에 적용하고 있다. 출력에서 실제 특징을 다시 얻고 마스크의 의미·경계 정확성을 검증해야 한다. 정답 마스크는 비교 기준으로 쓸 수 있지만, 제출물의 기하를 대신하면 안 된다.

## 2. 정답 종류가 공개 임계값에 들어간다 — P1

[정책 생성기](E:/I-mage-not-AI/benchmarks/prepare_multimetric_icon_dataset.py:167)는 숨긴 `fault`를 읽는다.

```python
center_limit = clean_offset + (0.01 if fault == 'center' else 0.2)
symmetry_limit = 0.98 if fault == 'symmetry' else 0.0
```

이미지를 열지 않고 manifest의 임계값만 읽는 간단한 분류기로 중심 4개·대칭 4개, 총 **8/24개**의 결함 종류를 모두 맞혔다. 실제 agent가 이 단서를 이용했다고 단정하지는 않는다. 평가 입력이 라벨과 독립적이지 않다는 것은 확인된다. 특히 symmetry IoU는 [0,1]이므로 0 이상이라는 조건은 유효한 어떤 마스크도 탈락시키지 않는다.

[preflight](E:/I-mage-not-AI/benchmarks/prepare_multimetric_ab.py:93)는 CLI가 의도한 FAIL 규칙과 정확히 일치하지 않는 케이스를 거부한다. 이 설계는 알고리즘 회귀 fixture에는 적절하지만, 같은 선별 표본의 100%를 일반 탐지 능력의 검증으로 제시할 수 없다. 라벨과 무관한 디자인 정책을 먼저 고정하고 보지 않은 표본에서 평가해야 한다. 데이터 누출과 주장 대상 분포의 문제는 [Kapoor & Narayanan, Patterns 2023](https://doi.org/10.1016/j.patter.2023.100804)의 분석과 연결된다. 이 논문이 우리 저장소를 직접 평가한 것은 아니며 적용 판단은 이번 코드 증거에서 도출했다.

## 3. 수치 구현이 맞다는 근거와 품질 의미의 한계

- `.venv/Scripts/python.exe -m pytest -q tests/test_algorithm_gold_values.py --basetemp E:/CodexTemp/WindowsTemp/imreview-math-audit-20261031`: **6 passed in 10.93s**.
- 현재 scalar/vectorized ΔE00 구현을 Sharma/Wu/Dalal 저자 공개 34개 참조쌍과 독립 비교: 최대 절대 오차 **4.9498977e-05**, 공개값 반올림 허용오차 0.00005 이내. [저자 자료와 논문](https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/).
- 이 검증은 산식의 수치 정확성에 대한 근거다. `ΔE00 ≤ 0.1`이라는 아이콘 정책의 타당성이나 전체 이미지의 미감을 보증하지 않는다.
- 현재 Lab20 bin에서 회색 RGB94↔95는 ΔE00≈0.364인데 다른 bin, RGB100↔140은 ΔE00≈15.870인데 같은 bin이다. bin count는 고정 양자화 수이지 지각적으로 구별되는 색 수가 아니다.
- 알파=1인 모서리 픽셀 하나는 전체 알파 질량의 약 9.57e-7만 차지해도 여백 0.25를 0으로 바꾼다. 엄격한 알파 오염 검사를 원하면 유용하지만, 육안 중심/여백과 동일하다고 해석하면 안 된다.
- 보석 RGB와 모든 alpha/마스크를 보존하고 나머지 내부 RGB를 순열로 섞으면 전체 팔레트·중심·여백·보석 색차·마스크 지표가 보존된다. 실제 메모리 실험에서 가시 픽셀 5,957개 중 3,765개의 RGB가 바뀌었다. 이 묶음은 내부 구성이 크게 훼손된 이미지와 정상 이미지를 같은 측정 벡터로 보낼 수 있다. 상세 수학 근거는 [수학 검토](E:/I-mage-not-AI/artifacts/metric-audit-2026-10-31/math-review.md)에 있다.

## 4. 진단 점수도 채점 계약을 수정해야 한다

[채점기](E:/I-mage-not-AI/benchmarks/score_multimetric_ab.py:118)는 CLI arm의 진단을 agent 응답 대신 raw CLI FAIL 결과로 덮어쓴다. AO는 자유문 evidence/action을 문자열로 읽는다. 따라서 현재 점수는 두 agent가 진단 결과를 이해하고 보고하는 능력을 동일한 출력 계약으로 비교하지 않는다. 도구를 포함한 pipeline finding 점수로 정의하려면 양 arm에서 동일한 표준 finding 제출을 받아야 한다.

문자열 채점기는 실제로 `No color defect was found.`를 color, `There is no overlap.`을 overlap, `No detached components.`를 components로 반환했다. `absent`를 overlap으로 매핑하는 것도 가림/결손/겹침을 혼동할 수 있다. AO 매핑은 이미 결과를 본 뒤 이번 대화에서 조정되었으므로 사전 고정된 채점 계약도 아니었다. 새 평가에서는 구조화된 범주와 실패/무결함 판단을 고정한 뒤 새 holdout을 사용해야 한다.

## 5. 24/24는 보편적 100%를 뜻하지 않는다

원본 clean SHA-256 고유값은 **4개**다. 같은 네 그림에 여섯 결함을 넣은 24개이며, 실제 생성 모델·스타일·해상도·마스크 오류에 대한 일반화 시험이 아니다. 정상 24개는 evaluator preflight용이고 두 agent에 섞여 제공되지 않았다. 정상 그림을 잘못 고치는 비율과 정상 케이스 specificity는 측정되지 않았다.

독립·동일 분포 Bernoulli 성공 시행이라고 임시 가정해도, 24/24의 exact Clopper–Pearson 양측 95% 성공률 구간은 **85.75%–100%**다. 결함 종류별 4/4는 **39.76%–100%**다. 24/24의 하한은 `(0.025) ** (1/24)`로 계산된다. [NIST exact 구간](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbici.htm). 이는 F1의 신뢰구간이 아니며, 실제 네 원본 재사용·선별 표본에는 일반화 구간으로 적용할 수 없다. 실행 횟수뿐 아니라 프롬프트/원본/모델/세션별 변동원을 반영해야 한다. [Bouthillier et al., MLSys 2021](https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html).

## 6. 평균 픽셀 일치율은 시각 품질 백분율이 아니다

`matching_RGBA_pixels / 16,384`는 배경도 전경과 똑같이 센다. 아이콘을 전부 지운 투명 이미지도 정답 배경과 일치하여 평균 **64.6942%**, 범위 **61.54%–68.10%**를 받았다. 따라서 기존 평균 일치율 96.06%는 시각 품질 96점으로 해석할 수 없다. 완전 일치 11/24 자체는 이 알려진 정답 복원 과제의 엄격한 사실로 유지된다.

전경/특징별 오류, 전체 exact match, 허용 수정 영역 밖 변화, 사용자 지각을 각각 보고해야 한다. 지각 유사도를 직접 사람 판단과 비교한 접근의 예는 [LPIPS, CVPR 2018](https://arxiv.org/abs/1801.03924)이다. LPIPS도 자연 이미지 검증 결과가 작은 픽셀 아이콘에 그대로 보장되지는 않는다.

## 7. 외부 지표와 비교하면 무엇이 빠졌는가

| 연구 | 검증 대상/방법 | 우리 평가에서 필요한 추가 증거 |
|---|---|---|
| [GenEval](https://arxiv.org/abs/2310.11513) | 객체·개수·위치·색의 텍스트 충실도, 사람 판단과 비교 | 방패/보석 같은 의미가 실제로 맞는지 검증 |
| [TIFA](https://openaccess.thecvf.com/content/ICCV2023/papers/Hu_TIFA_Accurate_and_Interpretable_Text-to-Image_Faithfulness_Evaluation_with_Question_Answering_ICCV_2023_paper.pdf) | 프롬프트별 질문 정답률, 사람 판단 상관 | 수학 규칙 밖의 의도·객체·관계 검증 |
| [Pick-a-Pic/PickScore](https://arxiv.org/abs/2305.01569) | 사람의 쌍별 선호와 선호 예측 | 미감·일관성·실제 사용 가능성의 블라인드 사람 평가 |
| [TS2](https://t2iscorescore.github.io/) | 오류 개수 순서에 대한 Spearman 상관, 오류 군집 간 KS 분리 | 실제/합성 오류·여러 심각도에서 각 지표가 올바른 순서로 반응하는지 메타평가 |
| [VBench](https://openaccess.thecvf.com/content/CVPR2024/html/Huang_VBench_Comprehensive_Benchmark_Suite_for_Video_Generative_Models_CVPR_2024_paper.html) | 시간·화질·의미의 16개 축과 사람 선호 검증 | 이미지 규칙·게임 trace만으로 일반 생성 영상의 시간/의미 품질을 주장하지 않음 |

TS2는 원래 텍스트-이미지 의미 충실도 지표의 평가다. 우리에게는 그 방법을 그대로 공인 점수처럼 옮기는 대신, 원본마다 정상→약한 결함→강한 결함→복합 결함을 구성하고 축별 순서·분리를 검증하는 설계로 참고할 수 있다. 서로 다른 결함 종류의 심각도를 근거 없이 단일 점수로 합치지 않는다. 자동 VQA·선호 모델을 더 붙여도 그 평가기의 아이콘 도메인 오류와 사람 일치를 다시 검증해야 한다.

## 우선순위와 다음 평가의 통과 조건

1. **필수 수정:** 라벨과 무관한 정책을 결함 주입 전에 고정; 제출 이미지 기반의 검증된 특징 마스크로 재평가; 잘못된/무수정 제출의 false PASS 차단.
2. **필수 수정:** 양 arm에 같은 구조화 진단 계약 적용; scorer/primary outcome을 실행 전에 고정; 새 holdout에서 평가.
3. **표본 확대:** 정상·단일·복합 결함, 여러 severity, 실제 생성 아이콘, 반투명·안티앨리어싱·mask 오류 포함. 같은 원본/프롬프트 계열은 평가 분할과 통계에서 군집으로 취급.
4. **평가 품질의 평가:** 각 지표의 민감도·특이도·임계값 안정성, 오류 심각도에 대한 순서·분리, 사람 판단과의 pairwise agreement 및 Spearman/Kendall 상관과 불확실성 보고.
5. **과제 성과:** 디자인 제약 충족, 실제 이미지의 기하/색 복원, 수정 금지 영역 보존, 사용자 선호·아이콘 인지/혼동/반응시간을 분리.
6. **반복/재현:** 모델 버전·예산·시간·도구 호출·의존성·실행 버전을 기록하고 여러 독립 trial의 paired 결과와 비용 보고.

## 이전 설명 정정

이전 답변과 README의 “여백 결함은 캔버스 밖 픽셀이 잘려 완전 복원이 불가능했다”는 설명은 잘못됐다. 네 입력의 오른쪽 alpha bbox 끝은 121 또는 117로 128 안에 있다. 원래 입력을 정확히 **-14 px 역이동하면 네 개 모두 정답 RGBA와 완전히 일치**한다. 실패한 복원은 -9/-5 px만 움직여 여백만 만족시키고 원래 위치를 복원하지 못한 결과다. 이 사실과 출력 마스크 검사 결함을 기존 README에 정정했다.

## 재현과 개별 보고서

- [재현 스크립트](E:/I-mage-not-AI/artifacts/metric-audit-2026-10-31/reproduce_audit.py): 저장된 파일만 읽고 감사 evidence/log만 작성한다.
- [재현 증거 JSON](E:/I-mage-not-AI/artifacts/metric-audit-2026-10-31/audit-evidence.json): 원본 코드 SHA, 실제 무수정 반례, threshold-only 예측, 역이동, 빈 이미지, 부정문, 가정하의 통계 구간.
- [수학·알고리즘 검토](E:/I-mage-not-AI/artifacts/metric-audit-2026-10-31/math-review.md)
- [실험 설계·통계 검토](E:/I-mage-not-AI/artifacts/metric-audit-2026-10-31/methodology-review.md)
- [외부 기준·문헌 비교](E:/I-mage-not-AI/artifacts/metric-audit-2026-10-31/external-review.md)

현재 발견된 P1은 평가 코드의 수정과 새 실험을 필요로 한다. 이번 작업은 이 문제들을 확인·기록하고 이전 설명을 정정했으며, 수정된 A/B를 새로 수행한 결과는 아니다.
