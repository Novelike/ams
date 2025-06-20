import React, { useState } from "react";
import { Box, Typography, Stepper, Step, StepLabel, Button, Paper } from "@mui/material";

const Registration = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [segmentationResults, setSegmentationResults] = useState(null);
  const [ocrResults, setOcrResults] = useState(null);
  const [assetData, setAssetData] = useState({
    model_name: "",
    detailed_model: "",
    serial_number: "",
    manufacturer: "",
    site: "",
    asset_type: "",
    user: ""
  });

  // Define the steps based on the backend workflow
  const steps = [
    { label: "이미지 업로드", description: "자산의 이미지를 업로드하세요" },
    { label: "세그멘테이션", description: "관심 영역을 식별합니다" },
    { label: "OCR", description: "이미지에서 텍스트를 추출합니다" },
    { label: "검토 및 편집", description: "추출된 정보를 검토하고 편집하세요" },
    { label: "챗봇 지원", description: "추가 정보를 위한 챗봇 지원" },
    { label: "등록", description: "자산을 등록합니다" },
    { label: "라벨 생성", description: "자산 라벨을 생성합니다" }
  ];

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setUploadedImage(null);
    setSegmentationResults(null);
    setOcrResults(null);
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

  // Render the content for the current step
  const getStepContent = (step) => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              이미지 업로드
            </Typography>
            <Typography variant="body1" paragraph>
              자산의 이미지를 업로드하세요. 이미지는 자산의 모델명, 일련번호 등이 잘 보이도록 촬영해주세요.
            </Typography>
            {/* Image upload component would go here */}
            <Button variant="contained" onClick={handleNext}>
              다음
            </Button>
          </Box>
        );
      case 1:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              세그멘테이션
            </Typography>
            <Typography variant="body1" paragraph>
              업로드된 이미지에서 관심 영역을 식별합니다.
            </Typography>
            {/* Segmentation component would go here */}
            <Box sx={{ display: "flex", flexDirection: "row", pt: 2 }}>
              <Button onClick={handleBack} sx={{ mr: 1 }}>
                이전
              </Button>
              <Button variant="contained" onClick={handleNext}>
                다음
              </Button>
            </Box>
          </Box>
        );
      case 2:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              OCR
            </Typography>
            <Typography variant="body1" paragraph>
              세그멘테이션된 이미지에서 텍스트를 추출합니다.
            </Typography>
            {/* OCR component would go here */}
            <Box sx={{ display: "flex", flexDirection: "row", pt: 2 }}>
              <Button onClick={handleBack} sx={{ mr: 1 }}>
                이전
              </Button>
              <Button variant="contained" onClick={handleNext}>
                다음
              </Button>
            </Box>
          </Box>
        );
      case 3:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              검토 및 편집
            </Typography>
            <Typography variant="body1" paragraph>
              추출된 정보를 검토하고 필요한 경우 편집하세요.
            </Typography>
            {/* Review and edit component would go here */}
            <Box sx={{ display: "flex", flexDirection: "row", pt: 2 }}>
              <Button onClick={handleBack} sx={{ mr: 1 }}>
                이전
              </Button>
              <Button variant="contained" onClick={handleNext}>
                다음
              </Button>
            </Box>
          </Box>
        );
      case 4:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              챗봇 지원
            </Typography>
            <Typography variant="body1" paragraph>
              추가 정보를 위해 챗봇의 도움을 받으세요.
            </Typography>
            {/* Chatbot component would go here */}
            <Box sx={{ display: "flex", flexDirection: "row", pt: 2 }}>
              <Button onClick={handleBack} sx={{ mr: 1 }}>
                이전
              </Button>
              <Button variant="contained" onClick={handleNext}>
                다음
              </Button>
            </Box>
          </Box>
        );
      case 5:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              등록
            </Typography>
            <Typography variant="body1" paragraph>
              자산을 등록합니다.
            </Typography>
            {/* Registration form component would go here */}
            <Box sx={{ display: "flex", flexDirection: "row", pt: 2 }}>
              <Button onClick={handleBack} sx={{ mr: 1 }}>
                이전
              </Button>
              <Button variant="contained" onClick={handleNext}>
                다음
              </Button>
            </Box>
          </Box>
        );
      case 6:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              라벨 생성
            </Typography>
            <Typography variant="body1" paragraph>
              자산 라벨을 생성합니다.
            </Typography>
            {/* Label generation component would go here */}
            <Box sx={{ display: "flex", flexDirection: "row", pt: 2 }}>
              <Button onClick={handleBack} sx={{ mr: 1 }}>
                이전
              </Button>
              <Button variant="contained" onClick={handleReset}>
                처음으로
              </Button>
            </Box>
          </Box>
        );
      default:
        return "Unknown step";
    }
  };

  return (
    <Box sx={{ marginBottom: "30px" }}>
      <Typography variant="h4" component="h1" gutterBottom>
        자산 등록
      </Typography>
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {steps.map((step) => (
            <Step key={step.label}>
              <StepLabel>{step.label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Paper>
      
      <Paper sx={{ p: 3 }}>
        {getStepContent(activeStep)}
      </Paper>
    </Box>
  );
};

export default Registration;