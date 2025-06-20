import React, { useState } from "react";
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Grid,
  Button,
  IconButton,
  Chip
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import FilterListIcon from "@mui/icons-material/FilterList";
import VisibilityIcon from "@mui/icons-material/Visibility";

const AssetList = () => {
  // State for pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  
  // State for filtering
  const [filters, setFilters] = useState({
    site: "",
    assetType: "",
    user: "",
    manufacturer: "",
    searchTerm: ""
  });
  
  // State for sorting
  const [sortBy, setSortBy] = useState("registration_date");
  const [sortDirection, setSortDirection] = useState("desc");
  
  // State for showing filter panel
  const [showFilters, setShowFilters] = useState(false);
  
  // Mock data for sites and asset types
  const sites = ["판교 본사", "고양 지사", "압구정 LF", "마곡 LG Science Park", "역삼 GS 타워"];
  const assetTypes = ["laptop", "desktop", "monitor", "keyboard", "mouse", "pad", "bag", "other"];
  
  // Mock data for assets (in a real app, this would come from an API call)
  const [assets, setAssets] = useState([
    {
      id: "1",
      asset_number: "AMS-2023-001",
      model_name: "ThinkPad X1 Carbon",
      serial_number: "PF-2X4N7",
      manufacturer: "Lenovo",
      site: "판교 본사",
      asset_type: "laptop",
      user: "김철수",
      registration_date: "2023-01-15"
    },
    {
      id: "2",
      asset_number: "AMS-2023-002",
      model_name: "Dell XPS 15",
      serial_number: "DL-9X5T7",
      manufacturer: "Dell",
      site: "고양 지사",
      asset_type: "laptop",
      user: "이영희",
      registration_date: "2023-02-10"
    },
    {
      id: "3",
      asset_number: "AMS-2023-003",
      model_name: "LG Gram 17",
      serial_number: "LG-17Z90P-K",
      manufacturer: "LG",
      site: "마곡 LG Science Park",
      asset_type: "laptop",
      user: "박지민",
      registration_date: "2023-03-05"
    }
  ]);
  
  // Total count (in a real app, this would come from the API)
  const totalCount = 100;
  
  // Handle page change
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
    // In a real app, this would trigger a new API call with the updated page
  };
  
  // Handle rows per page change
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
    // In a real app, this would trigger a new API call with the updated page size
  };
  
  // Handle filter change
  const handleFilterChange = (event) => {
    const { name, value } = event.target;
    setFilters(prevFilters => ({
      ...prevFilters,
      [name]: value
    }));
    // In a real app, this would trigger a new API call with the updated filters
  };
  
  // Handle search
  const handleSearch = () => {
    // In a real app, this would trigger a new API call with the search term
    console.log("Searching for:", filters.searchTerm);
  };
  
  // Handle sort change
  const handleSortChange = (column) => {
    if (sortBy === column) {
      // Toggle direction if clicking the same column
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      // Set new column and default to ascending
      setSortBy(column);
      setSortDirection("asc");
    }
    // In a real app, this would trigger a new API call with the updated sort
  };
  
  // Toggle filter panel
  const toggleFilters = () => {
    setShowFilters(!showFilters);
  };
  
  // Clear all filters
  const clearFilters = () => {
    setFilters({
      site: "",
      assetType: "",
      user: "",
      manufacturer: "",
      searchTerm: ""
    });
    // In a real app, this would trigger a new API call with cleared filters
  };
  
  // Get asset type label in Korean
  const getAssetTypeLabel = (type) => {
    const typeMap = {
      laptop: "노트북",
      desktop: "데스크탑",
      monitor: "모니터",
      keyboard: "키보드",
      mouse: "마우스",
      pad: "패드",
      bag: "가방",
      other: "기타"
    };
    return typeMap[type] || type;
  };
  
  return (
    <Box sx={{ marginBottom: "30px" }}>
      <Typography variant="h4" component="h1" gutterBottom>
        자산 목록
      </Typography>
      
      {/* Search and filter bar */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              fullWidth
              label="검색"
              name="searchTerm"
              value={filters.searchTerm}
              onChange={handleFilterChange}
              placeholder="모델명, 일련번호, 자산번호 등"
              InputProps={{
                endAdornment: (
                  <IconButton onClick={handleSearch}>
                    <SearchIcon />
                  </IconButton>
                )
              }}
            />
          </Grid>
          <Grid item>
            <Button
              variant="outlined"
              startIcon={<FilterListIcon />}
              onClick={toggleFilters}
            >
              필터
            </Button>
          </Grid>
          {Object.entries(filters).map(([key, value]) => 
            key !== "searchTerm" && value && (
              <Grid item key={key}>
                <Chip 
                  label={`${key === "site" ? "사이트" : 
                          key === "assetType" ? "유형" : 
                          key === "user" ? "사용자" : 
                          "제조사"}: ${key === "assetType" ? getAssetTypeLabel(value) : value}`} 
                  onDelete={() => handleFilterChange({ target: { name: key, value: "" } })}
                />
              </Grid>
            )
          )}
        </Grid>
        
        {/* Filter panel */}
        {showFilters && (
          <Box sx={{ mt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>사이트</InputLabel>
                  <Select
                    name="site"
                    value={filters.site}
                    onChange={handleFilterChange}
                    label="사이트"
                  >
                    <MenuItem value="">전체</MenuItem>
                    {sites.map(site => (
                      <MenuItem key={site} value={site}>{site}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>자산 유형</InputLabel>
                  <Select
                    name="assetType"
                    value={filters.assetType}
                    onChange={handleFilterChange}
                    label="자산 유형"
                  >
                    <MenuItem value="">전체</MenuItem>
                    {assetTypes.map(type => (
                      <MenuItem key={type} value={type}>{getAssetTypeLabel(type)}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="사용자"
                  name="user"
                  value={filters.user}
                  onChange={handleFilterChange}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="제조사"
                  name="manufacturer"
                  value={filters.manufacturer}
                  onChange={handleFilterChange}
                />
              </Grid>
              <Grid item xs={12}>
                <Button variant="outlined" onClick={clearFilters}>
                  필터 초기화
                </Button>
              </Grid>
            </Grid>
          </Box>
        )}
      </Paper>
      
      {/* Asset table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>자산 번호</TableCell>
                <TableCell>모델명</TableCell>
                <TableCell>일련번호</TableCell>
                <TableCell>제조사</TableCell>
                <TableCell>사이트</TableCell>
                <TableCell>유형</TableCell>
                <TableCell>사용자</TableCell>
                <TableCell>등록일</TableCell>
                <TableCell>상세</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {assets.map((asset) => (
                <TableRow key={asset.id}>
                  <TableCell>{asset.asset_number}</TableCell>
                  <TableCell>{asset.model_name}</TableCell>
                  <TableCell>{asset.serial_number}</TableCell>
                  <TableCell>{asset.manufacturer}</TableCell>
                  <TableCell>{asset.site}</TableCell>
                  <TableCell>{getAssetTypeLabel(asset.asset_type)}</TableCell>
                  <TableCell>{asset.user}</TableCell>
                  <TableCell>{asset.registration_date}</TableCell>
                  <TableCell>
                    <IconButton size="small">
                      <VisibilityIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={totalCount}
          page={page}
          onPageChange={handleChangePage}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[5, 10, 25, 50]}
          labelRowsPerPage="페이지당 행 수:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} / ${count}`}
        />
      </Paper>
    </Box>
  );
};

export default AssetList;