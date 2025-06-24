// Registration utility functions

/**
 * 텍스트에서 제목과 내용을 분리하여 실제 값만 추출
 * @param {string} text - 원본 텍스트
 * @returns {Object} - {category, value, confidence}
 */
export const extractValueFromText = (text) => {
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

    // 제목에서 카테고리 추출
    const category = categorizeFromTitle(title);

    // 내용에서 실제 값 추출 (괄호 제거, 불필요한 텍스트 정리)
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

/**
 * 제목에서 카테고리 분류
 * @param {string} title - 제목 텍스트
 * @returns {string} - 카테고리
 */
export const categorizeFromTitle = (title) => {
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

/**
 * 내용 텍스트 정리 (괄호, 불필요한 텍스트 제거)
 * @param {string} content - 내용 텍스트
 * @returns {string} - 정리된 텍스트
 */
export const cleanContent = (content) => {
  if (!content) return '';

  let cleaned = content.trim();

  // 괄호와 괄호 안의 내용 제거: (모델명), [시리얼] 등
  cleaned = cleaned.replace(/\([^)]*\)/g, '').trim();
  cleaned = cleaned.replace(/\[[^\]]*\]/g, '').trim();

  // 불필요한 접두사 제거 (더 정확한 패턴 사용)
  // "기자재의 명칭제품명칭" -> "명칭제품명칭"
  // "상호명제조업체명" -> "제조업체명"
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

/**
 * Categorizes text based on content (기본 키워드 기반 분류)
 * @param {string} text - The text to categorize
 * @returns {string} - The category
 */
export const categorizeText = (text) => {
  const lowerText = text.toLowerCase();

  // 기본 키워드 기반 분류 (무한 재귀 방지를 위해 extractValueFromText 호출 제거)
  if (lowerText.includes('모델') || lowerText.includes('model')) return 'model';
  if (lowerText.includes('제조') || lowerText.includes('manufacturer')) return 'manufacturer';
  if (lowerText.includes('시리얼') || lowerText.includes('serial')) return 'serial';
  if (lowerText.includes('번호') || lowerText.includes('number')) return 'number';
  if (lowerText.includes('전압') || lowerText.includes('voltage')) return 'spec';
  if (lowerText.includes('컴퓨터') || lowerText.includes('노트북')) return 'product';

  return 'other';
};

/**
 * Returns color for a category
 * @param {string} category - The category
 * @returns {string} - The color code
 */
export const getCategoryColor = (category) => {
  const colors = {
    model: '#2196F3',
    manufacturer: '#4CAF50',
    serial: '#FF9800',
    number: '#9C27B0',
    spec: '#F44336',
    product: '#00BCD4',
    other: '#757575'
  };
  return colors[category] || colors.other;
};

/**
 * Exports OCR data to JSON
 * @param {string} uploadedImagePath - Path to the uploaded image
 * @param {Array} editableOcrData - OCR data
 * @param {Object} assetData - Asset data
 */
export const exportToJSON = (uploadedImagePath, editableOcrData, assetData) => {
  const exportData = {
    image_path: uploadedImagePath,
    ocr_results: editableOcrData,
    asset_data: assetData,
    export_timestamp: new Date().toISOString()
  };

  const dataStr = JSON.stringify(exportData, null, 2);
  const dataBlob = new Blob([dataStr], {type: 'application/json'});
  const url = URL.createObjectURL(dataBlob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `ocr_data_${new Date().toISOString().slice(0, 10)}.json`;
  link.click();

  URL.revokeObjectURL(url);
};

/**
 * Exports OCR data to CSV
 * @param {Array} editableOcrData - OCR data
 */
export const exportToCSV = (editableOcrData) => {
  const csvData = editableOcrData.map(item => ({
    ID: item.id,
    Text: item.text,
    Category: item.category,
    Confidence: item.confidence,
    Order: item.order
  }));

  const headers = Object.keys(csvData[0] || {});
  const csvContent = [
    headers.join(','),
    ...csvData.map(row => 
      headers.map(header => `"${row[header]}"`).join(',')
    )
  ].join('\n');

  const dataBlob = new Blob([csvContent], {type: 'text/csv'});
  const url = URL.createObjectURL(dataBlob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `ocr_data_${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();

  URL.revokeObjectURL(url);
};


/**
 * 텍스트가 카테고리 제목인지 실제 값인지 판단
 * @param {string} text - 분석할 텍스트
 * @returns {Object} - {isCategory: boolean, category: string}
 */
export const analyzeTextType = (text) => {
  if (!text || typeof text !== 'string') {
    return { isCategory: false, category: 'other' };
  }

  const cleanText = text.trim().toLowerCase();

  // 카테고리 제목 패턴들
  const categoryPatterns = [
    /^기자재의?\s*(명칭|제품명칭)/,
    /^상호명제조업체명?$/,
    /^제조자제조국가$/,
    /^정격전압$/,
    /^모델명$/,
    /^제조사$/,
    /^시리얼번호$/,
    /^s\/n$/
  ];

  // 카테고리 제목인지 확인
  for (const pattern of categoryPatterns) {
    if (pattern.test(cleanText)) {
      // 카테고리 타입 결정
      if (cleanText.includes('모델') || cleanText.includes('기자재') || cleanText.includes('명칭')) {
        return { isCategory: true, category: 'model' };
      } else if (cleanText.includes('제조') || cleanText.includes('상호명')) {
        return { isCategory: true, category: 'manufacturer' };
      } else if (cleanText.includes('시리얼') || cleanText.includes('s/n')) {
        return { isCategory: true, category: 'serial' };
      } else if (cleanText.includes('전압') || cleanText.includes('정격')) {
        return { isCategory: true, category: 'spec' };
      }
      return { isCategory: true, category: 'other' };
    }
  }

  return { isCategory: false, category: 'other' };
};

/**
 * 실제 값인지 판단하고 카테고리 추정
 * @param {string} text - 분석할 텍스트
 * @returns {Object} - {isValue: boolean, category: string, value: string}
 */
export const analyzeActualValue = (text) => {
  if (!text || typeof text !== 'string') {
    return { isValue: false, category: 'other', value: text };
  }

  const cleanText = text.trim();

  // 모델명 패턴 (괄호 안의 모델명, 컴퓨터 제품명)
  const modelPatterns = [
    /노트북\s*컴퓨터\(([^)]+)\)/, // 노트북 컴퓨터(15U50R)
    /컴퓨터\(([^)]+)\)/, // 컴퓨터(모델명)
    /\b[A-Z0-9]{4,}\b/, // 대문자+숫자 조합 (15U50R 등)
  ];

  for (const pattern of modelPatterns) {
    const match = cleanText.match(pattern);
    if (match) {
      const value = match[1] || match[0];
      if (value && value.length > 2) {
        return { isValue: true, category: 'model', value: value.trim() };
      }
    }
  }

  // 제조사 패턴 (회사명)
  const manufacturerPatterns = [
    /^(엘지전자|삼성전자|애플|델|레노버|HP|ASUS|MSI|LG|Samsung|Apple|Dell|Lenovo)/i,
    /^[가-힣]+전자/,
    /\(주\)/,
    /Inc\.|Ltd\.|Corp\./
  ];

  for (const pattern of manufacturerPatterns) {
    if (pattern.test(cleanText)) {
      // 회사명 정리
      let value = cleanText.split('/')[0].trim(); // 슬래시 앞부분만
      value = value.replace(/\(주\)/, '').trim();
      if (value.length > 1) {
        return { isValue: true, category: 'manufacturer', value };
      }
    }
  }

  // 전압/스펙 패턴
  const specPatterns = [
    /\d+\s*V/, // 전압
    /\d+\s*A/, // 전류
    /\d+\s*W/, // 전력
    /\d+\s*Hz/, // 주파수
  ];

  for (const pattern of specPatterns) {
    if (pattern.test(cleanText)) {
      return { isValue: true, category: 'spec', value: cleanText };
    }
  }

  // 시리얼 번호 패턴
  const serialPatterns = [
    /^[A-Z]{2,}\d{4,}/, // 대문자+숫자
    /^\d{8,}/, // 8자리 이상 숫자
    /^[A-Z0-9-]{6,}/ // 대문자+숫자+하이픈 조합
  ];

  for (const pattern of serialPatterns) {
    if (pattern.test(cleanText)) {
      return { isValue: true, category: 'serial', value: cleanText };
    }
  }

  return { isValue: false, category: 'other', value: cleanText };
};

/**
 * OCR 결과 전체를 분석하여 카테고리-값 매칭
 * @param {Object} ocrResults - OCR 결과 객체
 * @param {Object} confidence - 신뢰도 객체
 * @returns {Array} - 매칭된 데이터 배열
 */
export const analyzeOCRResults = (ocrResults, confidence) => {
  if (!ocrResults || typeof ocrResults !== 'object') {
    return [];
  }

  const textData = [];
  const results = [];

  // 1단계: 모든 텍스트를 순서대로 분석
  Object.keys(ocrResults).forEach(key => {
    if ((key.startsWith('text_') || key === 'full_text') && key !== 'combined_text') {
      const text = ocrResults[key];
      const conf = confidence[key] || 0;
      const order = key.startsWith('text_') ? parseInt(key.replace('text_', '')) : 0;

      const categoryAnalysis = analyzeTextType(text);
      const valueAnalysis = analyzeActualValue(text);

      results.push({
        key,
        text,
        confidence: conf,
        order,
        isCategory: categoryAnalysis.isCategory,
        categoryType: categoryAnalysis.category,
        isValue: valueAnalysis.isValue,
        valueCategory: valueAnalysis.category,
        extractedValue: valueAnalysis.value
      });
    }
  });

  // 순서대로 정렬
  results.sort((a, b) => a.order - b.order);

  // 2단계: 실제 값 우선 선택
  const foundValues = {
    model: null,
    manufacturer: null,
    serial: null,
    spec: null
  };

  // 실제 값들을 먼저 찾기
  results.forEach(item => {
    if (item.isValue && foundValues[item.valueCategory] === null) {
      foundValues[item.valueCategory] = {
        id: item.key,
        originalKey: item.key,
        text: item.extractedValue,
        originalText: item.text,
        confidence: item.confidence,
        category: item.valueCategory,
        order: item.order,
        source: 'actual_value'
      };
    }
  });

  // 3단계: 실제 값이 없는 카테고리는 기존 로직 사용
  results.forEach(item => {
    if (!item.isValue) {
      const extracted = extractValueFromText(item.text);
      if (extracted.category !== 'other' && foundValues[extracted.category] === null) {
        foundValues[extracted.category] = {
          id: item.key,
          originalKey: item.key,
          text: extracted.value,
          originalText: item.text,
          confidence: item.confidence,
          category: extracted.category,
          order: item.order,
          source: 'extracted'
        };
      }
    }
  });

  // 4단계: 결과 배열 생성
  Object.values(foundValues).forEach(item => {
    if (item !== null) {
      textData.push(item);
    }
  });

  // 순서대로 정렬
  textData.sort((a, b) => a.order - b.order);

  return textData;
};
