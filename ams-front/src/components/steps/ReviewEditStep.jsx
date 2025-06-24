import React, { useState, useMemo } from 'react';
import { Box, Typography, Button, TextField, IconButton } from "@mui/material";
import { Add, Download, Edit, Delete, Save, Cancel } from "@mui/icons-material";
import { DataGrid } from '@mui/x-data-grid';
import { exportToJSON, exportToCSV } from '../../utils/registrationUtils';

/**
 * ReviewEditStep component for the fourth step of registration
 * @param {Object} props - Component props
 * @param {Array} props.editableOcrData - OCR data that can be edited
 * @param {string} props.editingId - ID of the item being edited
 * @param {Function} props.onEditStart - Function to start editing
 * @param {Function} props.onEditSave - Function to save edits
 * @param {Function} props.onEditCancel - Function to cancel editing
 * @param {Function} props.onDelete - Function to delete item
 * @param {Function} props.onAddNew - Function to add new item
 * @param {Object} props.draggedItem - Currently dragged item
 * @param {Function} props.onDragStart - Function to handle drag start
 * @param {Function} props.onDragOver - Function to handle drag over
 * @param {Function} props.onDrop - Function to handle drop
 * @param {string} props.uploadedImagePath - Path to the uploaded image
 * @param {Object} props.assetData - Asset data
 */
const ReviewEditStep = ({ 
  editableOcrData,
  editingId,
  onEditStart,
  onEditSave,
  onEditCancel,
  onDelete,
  onAddNew,
  draggedItem,
  onDragStart,
  onDragOver,
  onDrop,
  uploadedImagePath,
  assetData
}) => {
  const [editingRowId, setEditingRowId] = useState(null);
  const [editingText, setEditingText] = useState('');

  // 필요한 데이터만 필터링 (모델명, 시리얼넘버, 제조사, 스펙)
  const filteredData = useMemo(() => {
    return editableOcrData.filter(item => 
      ['model', 'serial', 'manufacturer', 'spec'].includes(item.category)
    );
  }, [editableOcrData]);

  // 자산 정보 입력 필드용 상태
  const [assetInfo, setAssetInfo] = useState({
    model_name: '',
    serial_number: '',
    manufacturer: '',
    specs: ''
  });

  // DataGrid 컬럼 정의
  const columns = [
    { 
      field: 'category', 
      headerName: '구분', 
      width: 120, 
      editable: false,
      renderCell: (params) => {
        const categoryNames = {
          model: '모델명',
          serial: '시리얼번호',
          manufacturer: '제조사',
          spec: '스펙'
        };
        return categoryNames[params.value] || params.value;
      }
    },
    { 
      field: 'text', 
      headerName: '내용', 
      width: 300, 
      editable: false,
      renderCell: (params) => {
        if (editingRowId === params.id) {
          return (
            <TextField
              value={editingText}
              onChange={(e) => setEditingText(e.target.value)}
              size="small"
              fullWidth
              variant="standard"
            />
          );
        }
        return params.value;
      }
    },
    { 
      field: 'confidence', 
      headerName: '신뢰도', 
      width: 100,
      editable: false,
      renderCell: (params) => `${(params.value * 100).toFixed(1)}%`
    },
    {
      field: 'actions',
      headerName: '작업',
      width: 120,
      sortable: false,
      renderCell: (params) => {
        if (editingRowId === params.id) {
          return (
            <Box>
              <IconButton 
                size="small" 
                onClick={() => handleSaveEdit(params.row)}
                color="primary"
              >
                <Save />
              </IconButton>
              <IconButton 
                size="small" 
                onClick={handleCancelEdit}
                color="secondary"
              >
                <Cancel />
              </IconButton>
            </Box>
          );
        }
        return (
          <Box>
            <IconButton 
              size="small" 
              onClick={() => handleStartEdit(params.row)}
              color="primary"
            >
              <Edit />
            </IconButton>
            <IconButton 
              size="small" 
              onClick={() => onDelete(params.id)}
              color="error"
            >
              <Delete />
            </IconButton>
          </Box>
        );
      }
    }
  ];

  const handleStartEdit = (row) => {
    setEditingRowId(row.id);
    setEditingText(row.text);
  };

  const handleSaveEdit = (row) => {
    onEditSave(row.id, editingText, row.category);
    setEditingRowId(null);
    setEditingText('');
  };

  const handleCancelEdit = () => {
    setEditingRowId(null);
    setEditingText('');
  };

  const handleAssetInfoChange = (field, value) => {
    setAssetInfo(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        자산 정보 검토 및 편집
      </Typography>
      <Typography variant="body1" paragraph>
        추출된 데이터를 검토하고 편집하세요. 부족한 정보는 아래 입력 필드에서 직접 입력할 수 있습니다.
      </Typography>

      {/* 액션 버튼들 */}
      <Box sx={{ 
        mb: 3, 
        display: 'flex', 
        gap: 1, 
        flexWrap: 'wrap'
      }}>
        <Button
          variant="outlined"
          startIcon={<Add />}
          onClick={onAddNew}
        >
          항목 추가
        </Button>
        <Button
          variant="outlined"
          startIcon={<Download />}
          onClick={() => exportToJSON(uploadedImagePath, filteredData, { ...assetData, ...assetInfo })}
        >
          JSON 내보내기
        </Button>
        <Button
          variant="outlined"
          startIcon={<Download />}
          onClick={() => exportToCSV(filteredData)}
        >
          CSV 내보내기
        </Button>
      </Box>

      {/* OCR 데이터 테이블 */}
      {filteredData.length > 0 ? (
        <Box sx={{ height: 400, width: '100%', mb: 3 }}>
          <DataGrid
            rows={filteredData}
            columns={columns}
            pageSize={10}
            rowsPerPageOptions={[5, 10, 20]}
            disableSelectionOnClick
            autoHeight
            sx={{
              '& .MuiDataGrid-cell:focus': {
                outline: 'none',
              },
              '& .MuiDataGrid-row:hover': {
                backgroundColor: '#f5f5f5',
              },
            }}
          />
        </Box>
      ) : (
        <Box sx={{ 
          textAlign: 'center', 
          py: 4,
          mb: 3,
          border: '1px solid #e0e0e0',
          borderRadius: 1,
          backgroundColor: '#f5f5f5'
        }}>
          <Typography variant="body2" color="textSecondary">
            관련 OCR 데이터가 없습니다. (모델명, 시리얼번호, 제조사, 스펙 데이터만 표시됩니다)
          </Typography>
        </Box>
      )}

      {/* 자산 정보 입력 필드 */}
      <Box sx={{ 
        p: 3, 
        border: '1px solid #e0e0e0', 
        borderRadius: 1,
        backgroundColor: '#fafafa',
        mb: 3
      }}>
        <Typography variant="h6" gutterBottom>
          자산 정보 입력
        </Typography>
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
          gap: 2 
        }}>
          <TextField
            label="모델명"
            value={assetInfo.model_name}
            onChange={(e) => handleAssetInfoChange('model_name', e.target.value)}
            fullWidth
            size="small"
          />
          <TextField
            label="시리얼번호"
            value={assetInfo.serial_number}
            onChange={(e) => handleAssetInfoChange('serial_number', e.target.value)}
            fullWidth
            size="small"
          />
          <TextField
            label="제조사"
            value={assetInfo.manufacturer}
            onChange={(e) => handleAssetInfoChange('manufacturer', e.target.value)}
            fullWidth
            size="small"
          />
          <TextField
            label="스펙 정보"
            value={assetInfo.specs}
            onChange={(e) => handleAssetInfoChange('specs', e.target.value)}
            fullWidth
            multiline
            rows={2}
            size="small"
          />
        </Box>
      </Box>

      {/* 요약 정보 */}
      {filteredData.length > 0 && (
        <Box sx={{ 
          p: 2, 
          backgroundColor: '#e3f2fd', 
          borderRadius: 1,
          border: '1px solid #2196F3'
        }}>
          <Typography variant="subtitle1" gutterBottom>
            📊 데이터 요약
          </Typography>
          <Typography variant="body2">
            추출된 항목: {filteredData.length}개 | 
            평균 신뢰도: {filteredData.length > 0 ? (filteredData.reduce((sum, item) => sum + item.confidence, 0) / filteredData.length * 100).toFixed(1) : 0}% |
            카테고리: {Array.from(new Set(filteredData.map(item => item.category))).join(', ')}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default ReviewEditStep;
