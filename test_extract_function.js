// 실제 OCR 결과로 extractValueFromText 함수 테스트

// 함수들을 복사해서 테스트
const categorizeFromTitle = (title) => {
  const lowerTitle = title.toLowerCase();

  if (lowerTitle.includes('모델') || lowerTitle.includes('model') || 
      lowerTitle.includes('기자재') || lowerTitle.includes('명칭') || 
      lowerTitle.includes('제품명칭')) {
    return 'model';
  }

  if (lowerTitle.includes('제조') || lowerTitle.includes('manufacturer') || 
      lowerTitle.includes('상호명') || lowerTitle.includes('제조업체') || 
      lowerTitle.includes('제조자')) {
    return 'manufacturer';
  }

  if (lowerTitle.includes('시리얼') || lowerTitle.includes('serial') || 
      lowerTitle.includes('s/n') || lowerTitle.includes('sn')) {
    return 'serial';
  }

  if (lowerTitle.includes('전압') || lowerTitle.includes('voltage') || 
      lowerTitle.includes('정격') || lowerTitle.includes('스펙')) {
    return 'spec';
  }

  return 'other';
};

const cleanContent = (content) => {
  if (!content) return '';

  let cleaned = content.trim();

  // 괄호와 괄호 안의 내용 제거: (모델명), [시리얼] 등
  cleaned = cleaned.replace(/\([^)]*\)/g, '').trim();
  cleaned = cleaned.replace(/\[[^\]]*\]/g, '').trim();

  // 불필요한 접두사 제거 (더 정확한 패턴 사용)
  const unnecessaryPatterns = [
    /^기자재의\s*/gi,
    /^제품의\s*/gi,
    /^상품의\s*/gi,
    /^장비의\s*/gi,
    /^상호명(?=\S)/gi,  // 상호명 뒤에 공백이 없는 경우만
    /^제조자\s+/gi,     // 제조자 뒤에 공백이 있는 경우만
    /^제조국가\s*/gi
  ];

  for (const pattern of unnecessaryPatterns) {
    cleaned = cleaned.replace(pattern, '').trim();
  }

  // 연속된 공백을 하나로 정리
  cleaned = cleaned.replace(/\s+/g, ' ').trim();

  return cleaned;
};

const categorizeText = (text) => {
  const lowerText = text.toLowerCase();

  if (lowerText.includes('모델') || lowerText.includes('model')) return 'model';
  if (lowerText.includes('제조') || lowerText.includes('manufacturer')) return 'manufacturer';
  if (lowerText.includes('시리얼') || lowerText.includes('serial')) return 'serial';
  if (lowerText.includes('번호') || lowerText.includes('number')) return 'number';
  if (lowerText.includes('전압') || lowerText.includes('voltage')) return 'spec';
  if (lowerText.includes('컴퓨터') || lowerText.includes('노트북')) return 'product';

  return 'other';
};

const extractValueFromText = (text) => {
  if (!text || typeof text !== 'string') {
    return { category: 'other', value: text, confidence: 0 };
  }

  const cleanText = text.trim();

  // 패턴 1: "제목: 내용" 형태
  const colonPattern = /^([^:]+):\s*(.+)$/;
  const colonMatch = cleanText.match(colonPattern);

  if (colonMatch) {
    const title = colonMatch[1].trim();
    const content = colonMatch[2].trim();

    const category = categorizeFromTitle(title);
    const value = cleanContent(content);

    return { category, value, confidence: 0.9 };
  }

  // 패턴 2: "제목 내용" 형태 (공백으로 구분)
  const spacePattern = /^(모델명|제조사|시리얼번호|시리얼|제조자|제조업체|상호명|기자재|명칭|제품명칭)\s+(.+)$/;
  const spaceMatch = cleanText.match(spacePattern);

  if (spaceMatch) {
    const title = spaceMatch[1].trim();
    const content = spaceMatch[2].trim();

    const category = categorizeFromTitle(title);
    const value = cleanContent(content);

    return { category, value, confidence: 0.8 };
  }

  // 패턴 3: 괄호 안의 내용 추출 (모델명 등)
  const bracketPattern = /\(([^)]+)\)/;
  const bracketMatch = cleanText.match(bracketPattern);

  if (bracketMatch) {
    const bracketContent = bracketMatch[1].trim();
    // 괄호 안의 내용이 의미있는 값인지 확인
    if (bracketContent && bracketContent.length > 1 && 
        !bracketContent.includes('모델명') && !bracketContent.includes('시리얼') && 
        !bracketContent.includes('제조사') && !bracketContent.includes('스펙')) {

      const category = categorizeText(cleanText);
      return { category, value: bracketContent, confidence: 0.7 };
    }
  }

  // 패턴 4: 특정 복합 키워드 패턴 처리
  // "상호명제조업체명" -> "제조업체명" 또는 실제 제조사명 추출

  // 상호명 패턴
  if (cleanText.startsWith('상호명')) {
    const extracted = cleanText.replace(/^상호명/, '').trim();
    if (extracted && extracted.length > 0) {
      return { category: 'manufacturer', value: extracted, confidence: 0.7 };
    }
  }

  // 기자재 패턴
  if (cleanText.startsWith('기자재')) {
    let extracted = cleanText.replace(/^기자재의?\s*/, '').replace(/명칭|제품명칭/gi, '').trim();
    // 괄호 안의 내용이 의미없는 경우 괄호 제거
    if (extracted.includes('(모델명)') || extracted.includes('(시리얼)') || extracted.includes('(제조사)')) {
      extracted = extracted.replace(/\([^)]*\)/g, '').trim();
    }
    if (extracted && extracted.length > 0) {
      return { category: 'model', value: extracted, confidence: 0.7 };
    }
  }

  // 제조자 패턴
  if (cleanText.startsWith('제조자')) {
    const extracted = cleanText.replace(/^제조자/, '').replace(/제조국가/gi, '').trim();
    if (extracted && extracted.length > 0) {
      return { category: 'manufacturer', value: extracted, confidence: 0.7 };
    }
  }

  // 정격 패턴
  if (cleanText.startsWith('정격')) {
    const extracted = cleanText.replace(/^정격/, '').trim();
    if (extracted && extracted.length > 0) {
      return { category: 'spec', value: extracted, confidence: 0.7 };
    }
  }

  // 패턴 5: 특정 키워드가 포함된 텍스트에서 실제 값 추출
  const category = categorizeText(cleanText);

  if (category !== 'other') {
    // 카테고리가 식별된 경우 텍스트 정리 시도
    let cleanedValue = cleanContent(cleanText);

    // 추가 정리: 카테고리 관련 키워드 제거
    if (category === 'model') {
      cleanedValue = cleanedValue.replace(/^(기자재의?\s*|명칭\s*|제품명칭\s*|모델명?\s*)/gi, '').trim();
    } else if (category === 'manufacturer') {
      cleanedValue = cleanedValue.replace(/^(상호명\s*|제조업체명?\s*|제조사\s*|제조자\s*)/gi, '').trim();
    } else if (category === 'spec') {
      cleanedValue = cleanedValue.replace(/^(정격\s*|전압\s*|스펙\s*)/gi, '').trim();
    }

    // 정리된 값이 의미있는 경우에만 사용
    if (cleanedValue && cleanedValue !== cleanText && cleanedValue.length > 0) {
      return { category, value: cleanedValue, confidence: 0.6 };
    }
  }

  // 패턴 5: 일반 텍스트 (기존 로직)
  return { category, value: cleanText, confidence: 0.5 };
};

// 실제 OCR 결과로 테스트
const testCases = [
  "기자재의 명칭제품명칭 (모델명)",
  "노트북 컴퓨터(15U50R)",
  "상호명제조업체명",
  "엘지전자(주)/Tech-Front (Chongqing) Computer Co.",
  "제조자제조국가",
  "엘지전자(주)중국",
  "정격전압",
  "19 V = - = 3.42 A"
];

console.log("=== 실제 OCR 결과 테스트 ===");
testCases.forEach((text, index) => {
  const result = extractValueFromText(text);
  console.log(`${index + 1}. 입력: "${text}"`);
  console.log(`   결과: 카테고리="${result.category}", 값="${result.value}", 신뢰도=${result.confidence}`);
  console.log();
});
