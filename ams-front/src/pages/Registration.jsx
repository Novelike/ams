import React, {useState, useCallback, useEffect} from "react";
import {
	Box,
	Typography,
	Paper,
	Dialog,
	DialogTitle,
	DialogContent,
	DialogActions
} from "@mui/material";
import {useDropzone} from "react-dropzone";
import {registrationApi} from "../services/api.js";
import {categorizeText, extractValueFromText, analyzeOCRResults} from "../utils/registrationUtils";
import api from "../services/api.js";


// Components
import RegistrationHeader from "../components/RegistrationHeader";
import RegistrationFooter from "../components/RegistrationFooter";
import ImageUploadStep from "../components/steps/ImageUploadStep";
import SegmentationStep from "../components/steps/SegmentationStep";
import OcrStep from "../components/steps/OcrStep";
import ReviewEditStep from "../components/steps/ReviewEditStep";
import CenteredLoader from "../components/CenteredLoader";

const Registration = () => {
	const [activeStep, setActiveStep] = useState(0);
	const [uploadedImage, setUploadedImage] = useState(null);
	const [uploadedImagePath, setUploadedImagePath] = useState(null);
	const [segmentationResults, setSegmentationResults] = useState(null);
	const [ocrResults, setOcrResults] = useState(null);
	const [editableOcrData, setEditableOcrData] = useState([]);
	const [editingId, setEditingId] = useState(null);
	const [draggedItem, setDraggedItem] = useState(null);
	const [assetData, setAssetData] = useState({
		model_name: "",
		detailed_model: "",
		serial_number: "",
		manufacturer: "",
		site: "",
		asset_type: "",
		user: ""
	});

	// Loading states
	const [loading, setLoading] = useState(false);
	const [loadingMessage, setLoadingMessage] = useState("처리 중...");
	const [progress, setProgress] = useState(0);
	const [uploadProgress, setUploadProgress] = useState(0);
	const [isUploading, setIsUploading] = useState(false);

	// SSE states
	const [jobId, setJobId] = useState(null);
	const [eventSource, setEventSource] = useState(null);
	const [currentMessage, setCurrentMessage] = useState("");

	const steps = [
		{label: "이미지 업로드", description: "자산의 이미지를 업로드하세요"},
		{label: "세그멘테이션", description: "관심 영역을 식별합니다"},
		{label: "OCR", description: "이미지에서 텍스트를 추출합니다"},
		{label: "검토 및 편집", description: "추출된 정보를 검토하고 편집하세요"},
		{label: "챗봇 지원", description: "추가 정보를 위한 챗봇 지원"},
		{label: "등록", description: "자산을 등록합니다"},
		{label: "라벨 생성", description: "자산 라벨을 생성합니다"}
	];

	useEffect(() => {
		return () => {
			if (uploadedImage) {
				URL.revokeObjectURL(uploadedImage);
			}
		};
	}, [uploadedImage]);

	// SSE cleanup on unmount
	useEffect(() => {
		return () => {
			if (eventSource) {
				eventSource.close();
			}
		};
	}, [eventSource]);

	// OCR 결과를 편집 가능한 데이터로 변환
	useEffect(() => {
		console.log("🔄 OCR 결과 변환 useEffect 실행 시작");
		console.log("🔄 현재 시간:", new Date().toISOString());
		console.log("🔄 ocrResults:", ocrResults);
		console.log("🔄 ocrResults 타입:", typeof ocrResults);
		console.log("🔄 ocrResults가 null인가?", ocrResults === null);
		console.log("🔄 ocrResults가 undefined인가?", ocrResults === undefined);

		if (ocrResults && ocrResults.results) {
			console.log("✅ OCR 결과 처리 시작");
			console.log("📊 OCR 결과 구조:", ocrResults);
			console.log("📊 OCR results 타입:", typeof ocrResults.results);
			console.log("📊 OCR results 키들:", Object.keys(ocrResults.results));
			console.log("📊 OCR results 키 개수:", Object.keys(ocrResults.results).length);

			const textData = [];
			const results = ocrResults.results;
			const confidence = ocrResults.confidence || {};

			// text_1, text_2, ... 형태의 데이터와 full_text를 배열로 변환
			Object.keys(results).forEach(key => {
				console.log(`🔍 키 검사: ${key}, startsWith('text_'): ${key.startsWith('text_')}, === 'full_text': ${key === 'full_text'}, !== 'combined_text': ${key !== 'combined_text'}`);

				// text_로 시작하거나 full_text인 경우 (combined_text는 제외)
				if ((key.startsWith('text_') || key === 'full_text') && key !== 'combined_text') {
					const id = key;
					const text = results[key];
					const conf = confidence[key] || 0;

					console.log(`✅ 텍스트 데이터 추가: ${key} = "${text}" (신뢰도: ${conf})`);

					// full_text의 경우 order를 0으로, text_N의 경우 N으로 설정
					let order = 0;
					if (key.startsWith('text_')) {
						order = parseInt(key.replace('text_', '')) || 0;
					} else if (key === 'full_text') {
						order = 1; // full_text는 첫 번째로 표시
					}

					// OCR 텍스트에서 실제 값 추출 및 카테고리 분류
					const extracted = extractValueFromText(text);

					textData.push({
						id: id,
						originalKey: key,
						text: extracted.value, // 실제 값만 추출
						originalText: text, // 원본 텍스트 보존
						confidence: conf,
						category: extracted.category, // 개선된 카테고리 분류
						order: order
					});
				} else {
					console.log(`❌ 키 제외됨: ${key}`);
				}
			});

			// 순서대로 정렬
			textData.sort((a, b) => a.order - b.order);
			console.log("📋 최종 편집 가능한 OCR 데이터:", textData);
			console.log("📋 편집 가능한 데이터 개수:", textData.length);
			console.log("🔄 setEditableOcrData 호출 중...");
			setEditableOcrData(textData);
			console.log("✅ setEditableOcrData 호출 완료");
		} else {
			console.log("❌ OCR 결과가 없거나 results 속성이 없음:", ocrResults);
			if (ocrResults) {
				console.log("❌ ocrResults는 존재하지만 results 속성이 없음");
				console.log("❌ ocrResults의 키들:", Object.keys(ocrResults));
			}
			console.log("🔄 빈 배열로 setEditableOcrData 설정 중...");
			setEditableOcrData([]);
			console.log("✅ 빈 배열 설정 완료");
		}
		console.log("🔄 OCR 결과 변환 useEffect 실행 완료");
	}, [ocrResults]);

	// SSE 연결 함수: jobId 하나만 처리하도록 만듭니다.
	const connectSSE = (jobId) => {
		// (1) 혹시 이전에 연 EventSource가 살아 있다면 닫아 줍니다.
		if (eventSource) {
			eventSource.close();
		}

		// (2) **중요**: 상대 경로로 호출하면 Vite의 proxy를 타서 CORS 없이 바로 백엔드로 요청이 갑니다.
		const url = `/api/registration/status/${jobId}`;

		// (3) EventSource 생성! 브라우저가 text/event-stream을 기다립니다.
		const evt = new EventSource(url);
		setEventSource(evt);
		setLoading(true);

		// (4) 연결이 열렸을 때(옵션)
		evt.onopen = () => {
			console.log("✅ SSE 연결이 열렸습니다:", url);
		};

		// (5) 서버에서 `data:` 프레임이 올 때마다 실행됩니다.
		evt.onmessage = (e) => {
			// 서버가 JSON.stringify로 보낸 문자열을 파싱
			const payload = JSON.parse(e.data);
			const { stage, message, result, progress } = payload;
			console.log("📡 SSE 수신:", payload);
			console.log("📡 SSE stage 값:", stage, typeof stage);
			console.log("📡 SSE message:", message);

			// OCR 진행 상황 처리
			if (progress !== undefined) {
				console.log("📊 진행률 업데이트:", progress);
				setProgress(progress);
			}

			// 단계별 메시지 처리 및 UI 업데이트
			const stageLower = stage ? stage.toLowerCase() : '';
			console.log("📡 SSE stage (소문자):", stageLower);

			// (6) UI에 상태 메시지를 띄워 줍니다 - OCR 세부 단계별로 다른 메시지 표시
			let newMessage = message; // 기본값은 서버에서 받은 메시지

			if (stageLower.startsWith('ocr_')) {
				switch (stageLower) {
					case 'ocr_start':
						newMessage = "OCR 시작...";
						console.log("🔄 OCR 시작...");
						break;
					case 'ocr_preprocessing':
						newMessage = "이미지 전처리 중...";
						console.log("🔄 OCR 전처리 중...");
						break;
					case 'ocr_detection':
						newMessage = "텍스트 영역 감지 중...";
						console.log("🔍 텍스트 영역 감지 중...");
						break;
					case 'ocr_recognition':
						newMessage = "텍스트 인식 중...";
						console.log("📝 텍스트 인식 중...");
						break;
					case 'ocr_postprocessing':
						newMessage = "결과 후처리 중...";
						console.log("⚙️ 후처리 중...");
						break;
					case 'ocr_done':
						newMessage = "OCR 완료!";
						console.log("✅ OCR 완료!");
						break;
					default:
						newMessage = message;
						break;
				}
			}

			// 메시지 업데이트 로그
			console.log("💬 메시지 업데이트:", newMessage);
			setCurrentMessage(newMessage);

			// (7) 완료 스테이지를 만나면 (대소문자 구분 없이 비교)
			console.log("🔍 완료 스테이지 체크:", stageLower, "result 존재 여부:", !!result);
			if (
				stageLower === "segment_done" ||
				stageLower === "ocr_done"     ||
				stageLower === "register_done"
			) {
				console.log("✅ 완료 스테이지 감지됨:", stageLower);

				// a) EventSource 닫고
				console.log("🔌 SSE 연결 종료 중...");
				evt.close();
				setEventSource(null);
				// b) 로딩 스피너 내리고
				console.log("⏳ 로딩 상태 해제 중...");
				setLoading(false);
				// c) 진행률 초기화
				console.log("📊 진행률 초기화 중...");
				setProgress(0);

				// d) 서버가 함께 준 결과(result)를 상태에 반영 (소문자로 일관성 있게 비교)
				if (stageLower === "segment_done" && result) {
					console.log("📊 세그멘테이션 결과 설정:", result);
					setSegmentationResults(result);
				}
				if (stageLower === "ocr_done") {
					console.log("🔍 OCR 완료 처리 시작 - result 존재 여부:", !!result);
					if (result) {
						console.log("📊 OCR 완료 - 받은 결과:", result);
						console.log("📊 OCR result.results:", result.results);
						console.log("📊 OCR result.confidence:", result.confidence);

						// 결과 구조 검증
						if (result.results && typeof result.results === 'object') {
							const ocrData = {
								results: result.results,
								confidence: result.confidence || {},
							};
							console.log("📊 설정할 OCR 데이터:", ocrData);
							console.log("📊 OCR 데이터 키 개수:", Object.keys(ocrData.results).length);
							setOcrResults(ocrData);
							console.log("✅ OCR 결과 상태 설정 완료");
						} else {
							console.error("❌ OCR 결과 구조가 올바르지 않음:", result);
							// 빈 결과라도 설정하여 다음 단계로 진행할 수 있도록 함
							setOcrResults({
								results: {},
								confidence: {},
							});
							console.log("⚠️ 빈 OCR 결과로 설정됨");
						}
					} else {
						console.error("❌ OCR 완료 이벤트에 result 데이터가 없음");
						// 빈 결과라도 설정하여 다음 단계로 진행할 수 있도록 함
						setOcrResults({
							results: {},
							confidence: {},
						});
						console.log("⚠️ result가 없어서 빈 OCR 결과로 설정됨");
					}
				}

				// e) 자동으로 다음 스텝으로 넘어갑니다.
				console.log("➡️ 다음 단계로 이동 중... (handleNext 호출)");
				handleNext();
				console.log("✅ handleNext 호출 완료");
			}
		};

		// (8) 에러가 나면 닫고 정리
		evt.onerror = (err) => {
			console.error("❌ SSE 오류:", err);
			evt.close();
			setEventSource(null);
			setLoading(false);
		};

		return evt;
	};


	const handleNext = () => {
		console.log("🔄 handleNext 함수 호출됨");
		setActiveStep((prevActiveStep) => {
			console.log("📈 activeStep 변경:", prevActiveStep, "->", prevActiveStep + 1);
			return prevActiveStep + 1;
		});
		console.log("✅ handleNext 함수 완료");
	};

	const handleBack = () => {
		setActiveStep((prevActiveStep) => prevActiveStep - 1);
	};

	const handleReset = () => {
		setActiveStep(0);
		if (uploadedImage) {
			URL.revokeObjectURL(uploadedImage);
		}
		setUploadedImage(null);
		setUploadedImagePath(null);
		setSegmentationResults(null);
		setOcrResults(null);
		setEditableOcrData([]);
		setAssetData({
			model_name: "",
			detailed_model: "",
			serial_number: "",
			manufacturer: "",
			site: "",
			asset_type: "",
			user: ""
		});
	};

	const handleSegmentation = async () => {
		if (!uploadedImagePath) return;

		try {
			console.log("🔄 세그멘테이션 시작:", uploadedImagePath);
			const result = await registrationApi.segmentImage(uploadedImagePath);
			console.log("🎉 세그멘테이션 API 응답:", result);

			// Check if result contains job_id for SSE connection
			if (result.job_id) {
				setJobId(result.job_id);
				setCurrentMessage("세그멘테이션 시작...");
				connectSSE(result.job_id);
			} else {
				// Fallback to direct result handling if no job_id
				console.log("🎉 세그멘테이션 완료:", result);
				setSegmentationResults(result);
				handleNext();
			}
		} catch (error) {
			console.error('세그멘테이션 오류:', error);
			setLoading(false);
		}
	};

	const handleSkipSegmentation = () => {
		console.log("⏭️ 세그멘테이션 단계 건너뛰기");
		setSegmentationResults({});
		handleNext();
	};

	const handleOCR = async () => {
		if (!uploadedImagePath) return;

		try {
			console.log("🔄 OCR 시작:", uploadedImagePath);

			// OCR 시작 전 상태 초기화
			setCurrentMessage("OCR 요청 중...");
			setProgress(0);
			setOcrResults(null); // 이전 결과 초기화
			setEditableOcrData([]); // 이전 편집 데이터 초기화

			const segmentData = segmentationResults || {};
			const result = await registrationApi.performOcr(uploadedImagePath, segmentData);
			console.log("🎉 OCR API 응답:", result);

			// Check if result contains job_id for SSE connection
			if (result.job_id) {
				setJobId(result.job_id);
				setCurrentMessage("OCR 시작...");
				console.log("🔗 SSE 연결 시작, Job ID:", result.job_id);
				connectSSE(result.job_id);
			} else {
				// Fallback to direct result handling if no job_id
				console.log("🎉 OCR 완료:", result);
				setOcrResults(result);
				handleNext();
			}
		} catch (error) {
			console.error('OCR 오류:', error);
			setLoading(false);
			setCurrentMessage("OCR 오류가 발생했습니다.");
		}
	};

	const handleAssetRegistration = async () => {
		try {
			console.log("🔄 자산 등록 시작:", assetData);
			const result = await registrationApi.registerAsset(assetData);
			console.log("🎉 자산 등록 API 응답:", result);

			// Check if result contains job_id for SSE connection
			if (result.job_id) {
				setJobId(result.job_id);
				setCurrentMessage("자산 등록 시작...");
				connectSSE(result.job_id);
			} else {
				// Fallback to direct result handling if no job_id
				console.log("🎉 자산 등록 완료:", result);
				handleNext();
			}
		} catch (error) {
			console.error('자산 등록 오류:', error);
			setLoading(false);
		}
	};

	const handleChatbotAssistance = async () => {
		try {
			setLoading(true);
			setProgress(0);
			setLoadingMessage("챗봇 지원 요청 중...");
			console.log("🔄 챗봇 지원 요청");
			const result = await registrationApi.getChatbotAssistance(
				ocrResults,
				assetData.model_name,
				assetData.serial_number,
				(progressEvent) => {
					const progressPercent = Math.round((progressEvent.loaded / progressEvent.total) * 100);
					setProgress(progressPercent);
					console.log(`📊 챗봇 지원 진행률: ${progressPercent}%`);
				}
			);
			console.log("🎉 챗봇 지원 완료:", result);
			if (result) {
				setAssetData(prev => ({
					...prev,
					...result
				}));
			}
			handleNext();
		} catch (error) {
			console.error('챗봇 지원 오류:', error);
		} finally {
			setLoading(false);
			setProgress(0);
		}
	};

	// OCR 데이터 편집 관련 함수들
	const handleEditStart = (id) => {
		setEditingId(id);
	};

	const handleEditSave = (id, newText, newCategory) => {
		setEditableOcrData(prev =>
			prev.map(item =>
				item.id === id
					? {...item, text: newText, category: newCategory}
					: item
			)
		);
		setEditingId(null);
	};

	const handleEditCancel = () => {
		setEditingId(null);
	};

	const handleDelete = (id) => {
		setEditableOcrData(prev => prev.filter(item => item.id !== id));
	};

	const handleAddNew = () => {
		const newId = `text_${editableOcrData.length + 1}`;
		const newItem = {
			id: newId,
			originalKey: newId,
			text: "",
			confidence: 1.0,
			category: "other",
			order: editableOcrData.length + 1
		};
		setEditableOcrData(prev => [...prev, newItem]);
		setEditingId(newId);
	};

	// 드래그 앤 드롭 관련 함수들
	const handleDragStart = (e, item) => {
		setDraggedItem(item);
		e.dataTransfer.effectAllowed = 'move';
	};

	const handleDragOver = (e) => {
		e.preventDefault();
		e.dataTransfer.dropEffect = 'move';
	};

	const handleDrop = (e, targetItem) => {
		e.preventDefault();

		if (!draggedItem || draggedItem.id === targetItem.id) {
			setDraggedItem(null);
			return;
		}

		const newData = [...editableOcrData];
		const draggedIndex = newData.findIndex(item => item.id === draggedItem.id);
		const targetIndex = newData.findIndex(item => item.id === targetItem.id);

		// 배열에서 드래그된 아이템을 제거하고 새 위치에 삽입
		const [draggedItemData] = newData.splice(draggedIndex, 1);
		newData.splice(targetIndex, 0, draggedItemData);

		// order 값 재정렬
		newData.forEach((item, index) => {
			item.order = index + 1;
		});

		setEditableOcrData(newData);
		setDraggedItem(null);
	};

	// Export functions have been moved to registrationUtils.js

	const onDrop = useCallback(async (acceptedFiles) => {
		console.log("✅ onDrop 호출됨, acceptedFiles:", acceptedFiles);

		if (acceptedFiles.length === 0) {
			console.warn("⚠️ 아무 파일도 선택되지 않았습니다.");
			return;
		}

		const file = acceptedFiles[0];
		console.log(`📄 선택된 파일: name=${file.name}, size=${file.size} bytes, type=${file.type}`);

		if (uploadedImage) {
			console.log("🗑️ 이전 preview URL 해제:", uploadedImage);
			URL.revokeObjectURL(uploadedImage);
		}

		const objectUrl = URL.createObjectURL(file);
		console.log("👁️ 새 preview URL 생성:", objectUrl);
		setUploadedImage(objectUrl);

		try {
			setIsUploading(true);
			setUploadProgress(0);
			console.log("🚀 서버로 업로드 시작: registrationApi.uploadImage");

			const response = await registrationApi.uploadImage(file, (progressEvent) => {
				const progress = Math.round((progressEvent.loaded / progressEvent.total) * 100);
				setUploadProgress(progress);
				console.log(`📊 업로드 진행률: ${progress}%`);
			});

			if (response) {
				console.log("🎉 업로드 성공! 서버 응답:", response);
				const imagePath = response.file_path || response.image_path || response.path;
				console.log("📁 설정된 이미지 경로:", imagePath);
				setUploadedImagePath(imagePath);

				handleNext();
			}
		} catch (error) {
			console.error('파일 업로드 오류:', error);
		} finally {
			setIsUploading(false);
			setUploadProgress(0);
		}
	}, [uploadedImage]);

	const {getRootProps, getInputProps, isDragActive} = useDropzone({
		onDrop,
		accept: {'image/*': []},
		maxFiles: 1,
	});

	// getCategoryColor function has been moved to registrationUtils.js

	// EditableCard component has been moved to its own file

	const getStepContent = (step) => {
		switch (step) {
			case 0:
				return (
					<ImageUploadStep
						dropzoneProps={getRootProps()}
						getInputProps={getInputProps}
						isDragActive={isDragActive}
						uploadedImage={uploadedImage}
						uploadProgress={uploadProgress}
						isUploading={isUploading}
					/>
				);

			case 1:
				return (
					<SegmentationStep
						uploadedImage={uploadedImage}
						onSegmentation={handleSegmentation}
						onSkipSegmentation={handleSkipSegmentation}
						isImagePathValid={!!uploadedImagePath}
						segmentationResults={segmentationResults}
					/>
				);

			case 2:
				return (
					<OcrStep
						uploadedImage={uploadedImage}
						onOcr={handleOCR}
						isImagePathValid={!!uploadedImagePath}
						ocrResults={ocrResults}
					/>
				);

			case 3:
				return (
					<ReviewEditStep
						editableOcrData={editableOcrData}
						editingId={editingId}
						onEditStart={handleEditStart}
						onEditSave={handleEditSave}
						onEditCancel={handleEditCancel}
						onDelete={handleDelete}
						onAddNew={handleAddNew}
						draggedItem={draggedItem}
						onDragStart={handleDragStart}
						onDragOver={handleDragOver}
						onDrop={handleDrop}
						uploadedImagePath={uploadedImagePath}
						assetData={assetData}
					/>
				);

			default:
				return <Typography>단계를 찾을 수 없습니다.</Typography>;
		}
	};

	// Determine if the next button should be disabled
	const isNextDisabled =
		(activeStep === 0 && !uploadedImagePath) ||
		(activeStep === 1 && !segmentationResults) ||
		(activeStep === 2 && !ocrResults);

	return (
		<Box sx={{
			position: 'relative',
			width: '100%',
			height: '100vh',
			display: 'flex',
			flexDirection: 'column',
			overflow: 'hidden'
		}}>
			{/* Header */}
			<RegistrationHeader
				activeStep={activeStep}
				steps={steps}
			/>

			{/* Main content - scrollable */}
			<Box sx={{
				flex: 1,
				overflow: 'auto',
				padding: 3,
				paddingTop: 1,
				paddingBottom: 1
			}}>
				<Paper elevation={3} sx={{
					padding: 3,
					marginBottom: 3
				}}>
					{getStepContent(activeStep)}
				</Paper>
			</Box>

			{/* Footer */}
			<RegistrationFooter
				activeStep={activeStep}
				totalSteps={steps.length}
				onBack={handleBack}
				onNext={handleNext}
				onReset={handleReset}
				isNextDisabled={isNextDisabled}
			/>

			{/* Centered Loader */}
			<CenteredLoader
				open={isUploading || loading || !!eventSource}
				message={isUploading
					? `업로드 중... ${uploadProgress}%`
					: (currentMessage || loadingMessage)
				}
				progress={isUploading ? uploadProgress : (progress > 0 ? progress : null)}
			/>
		</Box>
	);
};

export default Registration;
