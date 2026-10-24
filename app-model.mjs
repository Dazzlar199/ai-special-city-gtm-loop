const PRIORITY_WEIGHT = {
  '최우선': 40,
  '우선': 30,
  '추가확인': 20,
  '후순위': 10,
  '보류': 0,
};

export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

export function safeExternalUrl(value) {
  try {
    const base = typeof window === 'undefined' ? 'http://127.0.0.1/' : window.location.href;
    const url = new URL(value, base);
    return ['http:', 'https:', 'mailto:'].includes(url.protocol) ? url.href : '';
  } catch {
    return '';
  }
}

export function getPriorityWeight(priority) {
  return PRIORITY_WEIGHT[priority] ?? 0;
}

export function filterProspects(prospects, filters = {}) {
  const query = (filters.query ?? '').trim().toLocaleLowerCase('ko-KR');
  const status = filters.status ?? '전체';

  return prospects.filter((prospect) => {
    const searchable = [prospect.name, prospect.industry, prospect.region, prospect.evidence]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase('ko-KR');
    const matchesQuery = !query || searchable.includes(query);
    const matchesStatus = status === '전체' || prospect.status === status;
    return matchesQuery && matchesStatus;
  });
}

export function getTodayQueue(prospects) {
  return [...prospects]
    .filter((prospect) => prospect.priority !== '보류' && prospect.status !== '발송 금지')
    .sort((a, b) => getPriorityWeight(b.priority) - getPriorityWeight(a.priority));
}

export function mergeSavedState(prospects, saved = {}) {
  return prospects.map((prospect) => ({
    ...prospect,
    ...(saved[prospect.id] ?? {}),
    id: prospect.id,
  }));
}

export function summarizePipeline(prospects) {
  return prospects.reduce(
    (summary, prospect) => {
      summary.total += 1;
      if (['승인 대기', 'DM 준비'].includes(prospect.status)) summary.ready += 1;
      if (prospect.status === '회신 도착') summary.replied += 1;
      if (prospect.priority === '보류' || prospect.status === '발송 금지') summary.hold += 1;
      return summary;
    },
    { total: 0, ready: 0, replied: 0, hold: 0 },
  );
}

export function sortByDiscoveryScore(a, b) {
  return (b.discovery?.fit_score ?? -1) - (a.discovery?.fit_score ?? -1);
}

export function isReviewableCandidate(prospect) {
  return prospect.discovery?.gate_status !== 'rejected';
}

export function discoveryToProspect(candidate) {
  const evaluation = candidate.discovery ?? {};
  const evidence = (candidate.evidence ?? []).map((item) => [
    item.kind === 'search_result' ? '발견 근거' : (item.kind ?? '공개 근거'),
    `${item.excerpt || '공개 페이지'} · 확인 ${item.checked_at || '미상'}`,
  ]);
  const eligible = evaluation.outreach_eligible === true;
  const hasPublicContact = Boolean(candidate.public_contact?.value);
  const sourceLabels = {
    smartstore: '스마트스토어', instagram: 'Instagram', wadiz: '와디즈',
    tumblbug: '텀블벅', exhibitions: '박람회', fanfandaero: '판판대로', web: '공개 웹',
  };
  return {
    id: candidate.id,
    name: candidate.brand_name || '이름 확인 필요',
    initials: (candidate.brand_name || '?').slice(0, 1),
    priority: evaluation.fit_score >= 70 ? '우선' : evaluation.fit_score >= 50 ? '추가확인' : '후순위',
    status: eligible ? '승인 대기' : '조사 필요',
    industry: candidate.category || sourceLabels[candidate.source_type] || '업종 확인 필요',
    region: '지역 미확인',
    handle: hasPublicContact ? candidate.public_contact.value : '업무용 연락처 확인 필요',
    route: eligible ? '공개 업무용 연락처' : (hasPublicContact ? '공개 연락처 확인 · 발송 잠금' : '발송 불가 · 근거 보강 필요'),
    contactUrl: eligible ? (candidate.public_contact?.url || '') : '',
    channelUrl: candidate.official_url || candidate.evidence?.[0]?.url || '',
    storeUrl: candidate.source_type === 'smartstore' ? candidate.official_url : '',
    tagline: `${sourceLabels[candidate.source_type] || '공개 검색'}에서 발견 · 자동 발굴 후보`,
    summary: `자동 발굴 점수 ${evaluation.fit_score ?? 0}점입니다. 검색 결과는 후보 발견 근거일 뿐 최종 사실확인이 아닙니다. 공식 판매 페이지, 최근 60일 활동과 공개 업무용 연락처를 확인해야 아웃리치 대상으로 전환됩니다.`,
    stats: [
      ['공개 점수', `${evaluation.fit_score ?? 0}점`],
      ['판정', evaluation.gate_status === 'qualified' ? '검토 가능' : '근거 보강'],
      ['연락', eligible ? '가능' : (hasPublicContact ? '확인·잠금' : '미확인·잠금')],
      ['확인일', candidate.evidence?.[0]?.checked_at || '미상'],
    ],
    evidence: evidence.length ? evidence : [['공개 근거', '근거 URL이 없어 발송할 수 없습니다.']],
    questions: (evaluation.unknowns ?? []).map((field) => `${field} 항목을 공식 공개자료에서 확인`),
    messages: {
      first: eligible ? '공개 근거를 다시 확인한 뒤 브랜드 맞춤 문구를 작성하세요.' : (hasPublicContact ? '공개 연락처는 확인됐지만 나머지 적합성 근거를 보강하기 전에는 연락하지 않습니다.' : '공식 근거와 업무용 연락처를 확인하기 전에는 연락하지 않습니다.'),
      followup: '',
      email: '',
    },
    discovery: evaluation,
  };
}
