import React, { useState, useEffect } from 'react';
import {
	Box,
	Typography,
	TextField,
	Button,
	Paper,
	FormControl,
	InputLabel,
	Select,
	MenuItem,
	Dialog,
	DialogTitle,
	DialogContent,
	DialogActions,
	Chip
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { Search, Visibility, Refresh } from '@mui/icons-material';
import api from '../services/api';

const AssetList = () => {
	const [assets, setAssets] = useState([]);
	const [loading, setLoading] = useState(false);
	const [totalCount, setTotalCount] = useState(0);
	const [page, setPage] = useState(0);
	const [pageSize, setPageSize] = useState(20);

	// 필터 상태
	const [filters, setFilters] = useState({
		search: '',
		asset_type: '',
		site: '',
		manufacturer: ''
	});

	// 상세 정보 다이얼로그
	const [detailDialog, setDetailDialog] = useState(false);
	const [selectedAsset, setSelectedAsset] = useState(null);
	const [assetDetail, setAssetDetail] = useState(null);

	// DataGrid 컬럼 정의
	const columns = [
		{
			field: 'asset_number',
			headerName: '자산번호',
			width: 150,
			renderCell: (params) => (
				<Chip
					label={params.value}
					size="small"
					color="primary"
					variant="outlined"
				/>
			)
		},
		{ field: 'model_name', headerName: '모델명', width: 200 },
		{ field: 'manufacturer', headerName: '제조사', width: 120 },
		{ field: 'serial_number', headerName: '시리얼번호', width: 150 },
		{ field: 'site', headerName: '지점', width: 100 },
		{
			field: 'asset_type',
			headerName: '자산유형',
			width: 100,
			renderCell: (params) => {
				const typeColors = {
					laptop: 'primary',
					desktop: 'secondary',
					monitor: 'success',
					keyboard: 'warning',
					mouse: 'info',
					pad: 'error',
					bag: 'default',
					other: 'default'
				};
				return (
					<Chip
						label={params.value}
						size="small"
						color={typeColors[params.value] || 'default'}
					/>
				);
			}
		},
		{ field: 'user', headerName: '사용자', width: 100 },
		{
			field: 'registration_date',
			headerName: '등록일',
			width: 120,
			renderCell: (params) => {
				const date = new Date(params.value);
				return date.toLocaleDateString('ko-KR');
			}
		},
		{
			field: 'actions',
			headerName: '작업',
			width: 120,
			sortable: false,
			renderCell: (params) => (
				<Button
					size="small"
					startIcon={<Visibility />}
					onClick={() => handleViewDetail(params.row)}
					variant="outlined"
				>
					상세보기
				</Button>
			)
		}
	];

	// 자산 목록 조회
	const fetchAssets = async () => {
		setLoading(true);
		try {
			const params = {
				page: page + 1, // DataGrid는 0부터 시작하지만 API는 1부터 시작
				page_size: pageSize,
				...Object.fromEntries(
					Object.entries(filters).filter(([_, value]) => value !== '')
				)
			};

			const response = await api.get('/api/registration/assets/list', { params });
			setAssets(response.data.items);
			setTotalCount(response.data.total);
		} catch (error) {
			console.error('자산 목록 조회 실패:', error);
		} finally {
			setLoading(false);
		}
	};

	// 자산 상세 정보 조회
	const handleViewDetail = async (asset) => {
		setSelectedAsset(asset);
		setDetailDialog(true);

		try {
			const response = await api.get(`/api/registration/assets/${asset.asset_number}`);
			setAssetDetail(response.data);
		} catch (error) {
			console.error('자산 상세 정보 조회 실패:', error);
			setAssetDetail(null);
		}
	};

	// 필터 변경 핸들러
	const handleFilterChange = (field, value) => {
		setFilters(prev => ({
			...prev,
			[field]: value
		}));
	};

	// 검색 실행
	const handleSearch = () => {
		setPage(0); // 검색 시 첫 페이지로 이동
		fetchAssets();
	};

	// 초기 로드 및 페이지/페이지크기 변경 시 데이터 조회
	useEffect(() => {
		fetchAssets();
	}, [page, pageSize]);

	return (
		<Box sx={{ p: 3 }}>
			<Typography variant="h4" gutterBottom>
				자산 목록
			</Typography>

			{/* 필터 및 검색 영역 */}
			<Paper sx={{ p: 2, mb: 3 }}>
				<Box sx={{
					display: 'grid',
					gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
					gap: 2,
					mb: 2
				}}>
					<TextField
						label="검색"
						placeholder="자산번호, 모델명, 시리얼번호, 제조사"
						value={filters.search}
						onChange={(e) => handleFilterChange('search', e.target.value)}
						size="small"
						InputProps={{
							startAdornment: <Search sx={{ mr: 1, color: 'action.active' }} />
						}}
					/>

					<FormControl size="small">
						<InputLabel>자산유형</InputLabel>
						<Select
							value={filters.asset_type}
							onChange={(e) => handleFilterChange('asset_type', e.target.value)}
							label="자산유형"
						>
							<MenuItem value="">전체</MenuItem>
							<MenuItem value="laptop">노트북</MenuItem>
							<MenuItem value="desktop">데스크톱</MenuItem>
							<MenuItem value="monitor">모니터</MenuItem>
							<MenuItem value="keyboard">키보드</MenuItem>
							<MenuItem value="mouse">마우스</MenuItem>
							<MenuItem value="pad">패드</MenuItem>
							<MenuItem value="bag">가방</MenuItem>
							<MenuItem value="other">기타</MenuItem>
						</Select>
					</FormControl>

					<TextField
						label="지점"
						value={filters.site}
						onChange={(e) => handleFilterChange('site', e.target.value)}
						size="small"
					/>

					<TextField
						label="제조사"
						value={filters.manufacturer}
						onChange={(e) => handleFilterChange('manufacturer', e.target.value)}
						size="small"
					/>
				</Box>

				<Box sx={{ display: 'flex', gap: 1 }}>
					<Button
						variant="contained"
						startIcon={<Search />}
						onClick={handleSearch}
					>
						검색
					</Button>
					<Button
						variant="outlined"
						startIcon={<Refresh />}
						onClick={() => {
							setFilters({
								search: '',
								asset_type: '',
								site: '',
								manufacturer: ''
							});
							setPage(0);
							fetchAssets();
						}}
					>
						초기화
					</Button>
				</Box>
			</Paper>

			{/* 자산 목록 테이블 */}
			<Paper sx={{ height: 600, width: '100%' }}>
				<DataGrid
					rows={assets}
					columns={columns}
					rowCount={totalCount}
					loading={loading}
					paginationMode="server"
					page={page}
					pageSize={pageSize}
					onPageChange={setPage}
					onPageSizeChange={setPageSize}
					rowsPerPageOptions={[10, 20, 50, 100]}
					disableSelectionOnClick
					getRowId={(row) => row.asset_number}
					sx={{
						'& .MuiDataGrid-cell:focus': {
							outline: 'none',
						},
						'& .MuiDataGrid-row:hover': {
							backgroundColor: '#f5f5f5',
						},
					}}
				/>
			</Paper>

			{/* 자산 상세 정보 다이얼로그 */}
			<Dialog
				open={detailDialog}
				onClose={() => setDetailDialog(false)}
				maxWidth="md"
				fullWidth
			>
				<DialogTitle>
					자산 상세 정보
					{selectedAsset && (
						<Typography variant="subtitle1" color="textSecondary">
							{selectedAsset.asset_number}
						</Typography>
					)}
				</DialogTitle>
				<DialogContent>
					{assetDetail ? (
						<Box sx={{ mt: 1 }}>
							{/* 기본 정보 */}
							<Typography variant="h6" gutterBottom>
								기본 정보
							</Typography>
							<Box sx={{
								display: 'grid',
								gridTemplateColumns: 'repeat(2, 1fr)',
								gap: 2,
								mb: 3
							}}>
								<TextField
									label="자산번호"
									value={assetDetail.basic_info?.asset_number || ''}
									InputProps={{ readOnly: true }}
									size="small"
								/>
								<TextField
									label="모델명"
									value={assetDetail.basic_info?.model_name || ''}
									InputProps={{ readOnly: true }}
									size="small"
								/>
								<TextField
									label="시리얼번호"
									value={assetDetail.basic_info?.serial_number || ''}
									InputProps={{ readOnly: true }}
									size="small"
								/>
								<TextField
									label="제조사"
									value={assetDetail.basic_info?.manufacturer || ''}
									InputProps={{ readOnly: true }}
									size="small"
								/>
								<TextField
									label="지점"
									value={assetDetail.basic_info?.site || ''}
									InputProps={{ readOnly: true }}
									size="small"
								/>
								<TextField
									label="자산유형"
									value={assetDetail.basic_info?.asset_type || ''}
									InputProps={{ readOnly: true }}
									size="small"
								/>
							</Box>

							{/* 스펙 정보 */}
							{assetDetail.specs && Object.keys(assetDetail.specs).length > 0 && (
								<>
									<Typography variant="h6" gutterBottom>
										스펙 정보
									</Typography>
									<Box sx={{ mb: 3 }}>
                    <pre style={{
	                    backgroundColor: '#f5f5f5',
	                    padding: '16px',
	                    borderRadius: '4px',
	                    fontSize: '14px',
	                    overflow: 'auto'
                    }}>
                      {JSON.stringify(assetDetail.specs, null, 2)}
                    </pre>
									</Box>
								</>
							)}

							{/* OCR 결과 */}
							{assetDetail.ocr_results && Object.keys(assetDetail.ocr_results).length > 0 && (
								<>
									<Typography variant="h6" gutterBottom>
										OCR 결과
									</Typography>
									<Box sx={{ mb: 3 }}>
                    <pre style={{
	                    backgroundColor: '#f5f5f5',
	                    padding: '16px',
	                    borderRadius: '4px',
	                    fontSize: '14px',
	                    overflow: 'auto'
                    }}>
                      {JSON.stringify(assetDetail.ocr_results, null, 2)}
                    </pre>
									</Box>
								</>
							)}
						</Box>
					) : (
						<Typography>상세 정보를 불러오는 중...</Typography>
					)}
				</DialogContent>
				<DialogActions>
					<Button onClick={() => setDetailDialog(false)}>
						닫기
					</Button>
				</DialogActions>
			</Dialog>
		</Box>
	);
};

export default AssetList;
