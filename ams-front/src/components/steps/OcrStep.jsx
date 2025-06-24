import React from 'react';
import { Box, Typography, Button } from "@mui/material";

/**
 * OcrStep component for the third step of registration
 * @param {Object} props - Component props
 * @param {string} props.uploadedImage - URL of the uploaded image
 * @param {Function} props.onOcr - Function to handle OCR
 * @param {boolean} props.isImagePathValid - Whether the image path is valid
 * @param {Object} props.ocrResults - Results of OCR
 */
const OcrStep = ({ 
  uploadedImage, 
  onOcr, 
  isImagePathValid,
  ocrResults 
}) => {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        OCR (광학 문자 인식)
      </Typography>
      <Typography variant="body1" paragraph>
        이미지에서 텍스트를 추출합니다.
      </Typography>
      {uploadedImage && (
        <Box sx={{ marginBottom: 2 }}>
          <img
            src={uploadedImage}
            alt="OCR 대상 이미지"
            style={{
              maxWidth: '100%',
              height: 'auto',
              objectFit: 'contain',
            }}
          />
        </Box>
      )}
      <Button
        variant="contained"
        onClick={onOcr}
        disabled={!isImagePathValid}
      >
        OCR 실행
      </Button>
      {ocrResults && (
        <Box sx={{ marginTop: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            추출된 텍스트:
          </Typography>
          <Box sx={{ 
            backgroundColor: '#f5f5f5', 
            padding: 2, 
            borderRadius: 1,
            border: '1px solid #e0e0e0'
          }}>
            <Typography variant="body2" component="pre" sx={{ 
              whiteSpace: 'pre-wrap',
              margin: 0
            }}>
              {ocrResults?.results?.combined_text || 'No text extracted'}
            </Typography>
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default OcrStep;