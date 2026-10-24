import test from 'node:test';
import assert from 'node:assert/strict';

import {
  filterProspects,
  getPriorityWeight,
  getTodayQueue,
  mergeSavedState,
  summarizePipeline,
  sortByDiscoveryScore,
  isReviewableCandidate,
  discoveryToProspect,
  escapeHtml,
} from '../app-model.mjs';

const prospects = [
  { id: 'maom', name: '마옴집', priority: '최우선', status: '승인 대기', industry: '생활소품' },
  { id: 'nature', name: '자연서당', priority: '우선', status: '조사 필요', industry: '천연비누' },
  { id: 'hold', name: '심기록', priority: '보류', status: '발송 금지', industry: '도자기' },
];

test('검색어와 상태로 후보를 필터링한다', () => {
  assert.deepEqual(
    filterProspects(prospects, { query: '비누', status: '조사 필요' }).map((item) => item.id),
    ['nature'],
  );
});

test('오늘 할 일은 보류 후보를 제외하고 우선순위 순으로 정렬한다', () => {
  assert.deepEqual(getTodayQueue(prospects).map((item) => item.id), ['maom', 'nature']);
  assert.ok(getPriorityWeight('최우선') > getPriorityWeight('우선'));
});

test('저장된 상태와 메모는 원본 후보에 안전하게 합쳐진다', () => {
  const merged = mergeSavedState(prospects, {
    maom: { status: 'DM 준비', note: '내일 오전 확인' },
    missing: { status: '무시' },
  });
  assert.equal(merged[0].status, 'DM 준비');
  assert.equal(merged[0].note, '내일 오전 확인');
  assert.equal(merged.length, 3);
});

test('파이프라인 요약은 전체·접촉 준비·회신·보류를 계산한다', () => {
  const summary = summarizePipeline([
    ...prospects,
    { id: 'reply', priority: '우선', status: '회신 도착' },
  ]);
  assert.deepEqual(summary, { total: 4, ready: 1, replied: 1, hold: 1 });
});

test('발굴 후보는 점수순으로 정렬하고 제외 판정은 목록에서 뺀다', () => {
  const found = [
    { id: 'low', discovery: { fit_score: 55, gate_status: 'needs_research' } },
    { id: 'reject', discovery: { fit_score: 100, gate_status: 'rejected' } },
    { id: 'high', discovery: { fit_score: 80, gate_status: 'qualified' } },
  ];
  assert.deepEqual(found.filter(isReviewableCandidate).sort(sortByDiscoveryScore).map((item) => item.id), ['high', 'low']);
});

test('자동 발굴 후보는 검증 전 아웃리치가 잠긴 화면 모델로 변환된다', () => {
  const result = discoveryToProspect({
    id: 'lead-1',
    brand_name: '작은 브랜드',
    source_type: 'wadiz',
    official_url: 'https://example.com/brand',
    evidence: [{ url: 'https://example.com/brand', excerpt: '검색 결과', checked_at: '2026-10-24' }],
    discovery: { fit_score: 35, gate_status: 'needs_research', outreach_eligible: false, unknowns: ['public_contact'] },
  });
  assert.equal(result.status, '조사 필요');
  assert.equal(result.contactUrl, '');
  assert.match(result.summary, /자동 발굴/);
  assert.equal(result.stats[0][1], '35점');
});

test('공개 연락처가 확인된 후보는 발송 잠금 상태에서도 연락처를 표시한다', () => {
  const result = discoveryToProspect({
    id: 'lead-contact',
    brand_name: '연락 가능한 브랜드',
    source_type: 'wadiz',
    official_url: 'https://www.wadiz.io/web/campaign/detail/1',
    public_contact: { type: 'email', value: 'hello@example.com', url: 'mailto:hello@example.com' },
    discovery: { fit_score: 25, gate_status: 'needs_research', outreach_eligible: false, unknowns: ['own_product_count'] },
  });
  assert.equal(result.handle, 'hello@example.com');
  assert.equal(result.contactUrl, '');
  assert.match(result.route, /발송 잠금/);
});

test('외부 검색 결과를 HTML에 넣기 전에 특수문자를 이스케이프한다', () => {
  assert.equal(escapeHtml('<img src=x onerror="alert(1)">&'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;&amp;');
});
