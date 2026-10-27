# 컨택 로그

`log.csv` 한 줄 = 고객 1명과의 1:1 접점 1건. 공개 저장소에는 상대 이름·연락처를 올리지 않는다(`log.csv`는 익명 ID만, 원본은 로컬 `contacts/private/`, git 제외).

| 열 | 뜻 |
|---|---|
| date | KST 날짜 |
| id | C001부터 |
| channel | kmong_enterprise / kmong_inquiry / soomgo / wishket / landing / sns / fair / tender / referral(소개) |
| basis | request(상대 요청) / consent(대면 동의) / material_request(자료 요청) / tender(공고 응모). 소개(referral)는 상대가 소개자를 통해 먼저 만남·진단을 요청한 경우만 request로 센다 |
| basis_ref | 의뢰·요청서·공고 번호 (상대 식별 정보 제외) |
| segment | 업종·상품 수 구간 (예: 식품·SKU 5~10) |
| action | 보낸 것 (제안서·견적·답변·상담 약속) |
| result | 무응답 / 답장 / 상담 / 결제 / 거절(사유) |

증빙 이미지는 `docs/evidence/`에 개인정보(이름·전화·이메일·주소)를 모자이크한 사본만 올린다. 원본은 `contacts/private/evidence/`.
