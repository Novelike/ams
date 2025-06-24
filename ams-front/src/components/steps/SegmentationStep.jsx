import React from 'react';
import { Box, Typography, Button } from "@mui/material";

/**
 * SegmentationStep component for the second step of registration
 * @param {Object} props - Component props
 * @param {string} props.uploadedImage - URL of the uploaded image
 * @param {Function} props.onSegmentation - Function to handle segmentation
 * @param {Function} props.onSkipSegmentation - Function to skip segmentation
 * @param {boolean} props.isImagePathValid - Whether the image path is valid
 * @param {Object} props.segmentationResults - Results of segmentation
 */
const SegmentationStep = ({ 
  uploadedImage, 
  onSegmentation, 
  onSkipSegmentation, 
  isImagePathValid,
  segmentationResults 
}) => {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        세그멘테이션
      </Typography>
      <Typography variant="body1" paragraph>
        이미지에서 관심 영역을 식별합니다. 세그멘테이션을 통해 텍스트가 있는 영역을 찾아냅니다.
      </Typography>
      {uploadedImage && (
        <Box sx={{ marginBottom: 2 }}>
          <img
            src={uploadedImage}
            alt="세그멘테이션 대상 이미지"
            style={{
              maxWidth: '100%',
              height: 'auto',
              objectFit: 'contain',
            }}
          />
        </Box>
      )}
      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
        <Button
          variant="contained"
          onClick={onSegmentation}
          disabled={!isImagePathValid}
        >
          세그멘테이션 실행
        </Button>
        <Button
          variant="outlined"
          onClick={onSkipSegmentation}
          disabled={!isImagePathValid}
        >
          세그멘테이션 건너뛰기
        </Button>
      </Box>
      {segmentationResults && (
        <Box sx={{ marginTop: 2 }}>
          <Typography variant="subtitle1">
            세그멘테이션 완료!
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default SegmentationStep;