import React from 'react';
import { Box, Typography } from "@mui/material";
import UploadProgressBar from '../UploadProgressBar';

/**
 * ImageUploadStep component for the first step of registration
 * @param {Object} props - Component props
 * @param {Object} props.dropzoneProps - Props for the dropzone
 * @param {Function} props.getInputProps - Function to get input props from react-dropzone
 * @param {boolean} props.isDragActive - Whether a file is being dragged over
 * @param {string} props.uploadedImage - URL of the uploaded image
 * @param {number} props.uploadProgress - Upload progress (0-100)
 * @param {boolean} props.isUploading - Whether file is currently uploading
 */
const ImageUploadStep = ({ 
  dropzoneProps, 
  getInputProps, 
  isDragActive, 
  uploadedImage, 
  uploadProgress = 0, 
  isUploading = false 
}) => {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        이미지 업로드
      </Typography>
      <Typography variant="body1" paragraph>
        자산의 이미지를 업로드하세요. 이미지는 자산의 모델명, 일련번호 등이 잘 보이도록 촬영해주세요.
      </Typography>
      <Box
        {...dropzoneProps}
        sx={{
          border: '2px dashed #cccccc',
          borderRadius: '4px',
          padding: '20px',
          textAlign: 'center',
          cursor: 'pointer',
          marginBottom: 2,
          '&:hover': {
            borderColor: '#999999',
          },
          backgroundColor: isDragActive ? '#f0f0f0' : 'transparent',
        }}
      >
        <input {...getInputProps()} />
        {isDragActive ? (
          <Typography>파일을 여기에 드롭하세요...</Typography>
        ) : (
          <Typography>
            파일을 드래그 앤 드롭하거나 클릭하여 선택하세요
          </Typography>
        )}
      </Box>

      {/* Upload Progress Bar */}
      <UploadProgressBar progress={uploadProgress} show={isUploading} />

      {uploadedImage && (
        <Box sx={{ marginTop: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            미리보기:
          </Typography>
          <img
            src={uploadedImage}
            alt="업로드된 이미지"
            style={{
              maxWidth: '100%',
              height: 'auto',
              objectFit: 'contain',
            }}
          />
        </Box>
      )}
    </Box>
  );
};

export default ImageUploadStep;
