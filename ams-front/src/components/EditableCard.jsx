import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  IconButton,
  Chip
} from "@mui/material";
import {
  DragIndicator,
  Edit,
  Delete,
  Save,
  Cancel
} from "@mui/icons-material";
import { getCategoryColor } from '../utils/registrationUtils';

/**
 * EditableCard component for displaying and editing OCR data
 * @param {Object} props - Component props
 * @param {Object} props.item - OCR data item
 * @param {string} props.editingId - ID of the item being edited
 * @param {Function} props.onEditStart - Function to start editing
 * @param {Function} props.onEditSave - Function to save edits
 * @param {Function} props.onEditCancel - Function to cancel editing
 * @param {Function} props.onDelete - Function to delete item
 * @param {Object} props.draggedItem - Currently dragged item
 * @param {Function} props.onDragStart - Function to handle drag start
 * @param {Function} props.onDragOver - Function to handle drag over
 * @param {Function} props.onDrop - Function to handle drop
 */
const EditableCard = ({ 
  item, 
  editingId, 
  onEditStart, 
  onEditSave, 
  onEditCancel, 
  onDelete,
  draggedItem,
  onDragStart,
  onDragOver,
  onDrop
}) => {
  const [editText, setEditText] = useState(item.text);
  const [editCategory, setEditCategory] = useState(item.category);
  const isEditing = editingId === item.id;

  return (
    <Card
      sx={{
        mb: 1,
        cursor: 'grab',
        border: `2px solid ${getCategoryColor(item.category)}`,
        '&:hover': { boxShadow: 3 },
        opacity: draggedItem?.id === item.id ? 0.5 : 1
      }}
      draggable
      onDragStart={(e) => onDragStart(e, item)}
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, item)}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
          <DragIndicator sx={{ color: 'grey.500', mt: 0.5 }} />
          
          <Box sx={{ flexGrow: 1 }}>
            {isEditing ? (
              <Box>
                <TextField
                  fullWidth
                  multiline
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  size="small"
                  sx={{ mb: 1 }}
                />
                <TextField
                  select
                  value={editCategory}
                  onChange={(e) => setEditCategory(e.target.value)}
                  size="small"
                  SelectProps={{ native: true }}
                  sx={{ minWidth: 120 }}
                >
                  <option value="model">모델</option>
                  <option value="manufacturer">제조사</option>
                  <option value="serial">시리얼</option>
                  <option value="number">번호</option>
                  <option value="spec">사양</option>
                  <option value="product">제품</option>
                  <option value="other">기타</option>
                </TextField>
              </Box>
            ) : (
              <Box>
                <Typography variant="body1" sx={{ mb: 1 }}>
                  {item.text}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <Chip 
                    label={item.category} 
                    size="small"
                    sx={{ 
                      backgroundColor: getCategoryColor(item.category),
                      color: 'white'
                    }}
                  />
                  <Typography variant="caption" color="textSecondary">
                    신뢰도: {(item.confidence * 100).toFixed(1)}%
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {isEditing ? (
              <>
                <IconButton
                  size="small"
                  onClick={() => onEditSave(item.id, editText, editCategory)}
                  color="primary"
                >
                  <Save />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={onEditCancel}
                  color="secondary"
                >
                  <Cancel />
                </IconButton>
              </>
            ) : (
              <>
                <IconButton
                  size="small"
                  onClick={() => onEditStart(item.id)}
                  color="primary"
                >
                  <Edit />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => onDelete(item.id)}
                  color="error"
                >
                  <Delete />
                </IconButton>
              </>
            )}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export default EditableCard;