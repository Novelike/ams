import axios from 'axios';

// Create an axios instance with the default config
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    // You can add auth token here if needed
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle errors globally
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// Asset API functions
export const assetApi = {
  // Get all assets with pagination and filtering
  getAssets: async (page = 1, pageSize = 10, filters = {}, sortBy = null, sortDesc = false) => {
    const params = {
      page,
      page_size: pageSize,
      ...filters,
    };

    if (sortBy) {
      params.sort_by = sortBy;
      params.sort_desc = sortDesc;
    }

    const response = await api.get('/api/assets/list', { params });
    return response.data;
  },

  // Get asset by ID
  getAssetById: async (id) => {
    const response = await api.get(`/api/assets/list/${id}`);
    return response.data;
  },

  // Search assets
  searchAssets: async (query) => {
    const response = await api.get(`/api/assets/list/search/${query}`);
    return response.data;
  },

  // Get assets by site
  getAssetsBySite: async (site) => {
    const response = await api.get(`/api/assets/list/site/${site}`);
    return response.data;
  },

  // Get assets by type
  getAssetsByType: async (type) => {
    const response = await api.get(`/api/assets/list/type/${type}`);
    return response.data;
  },

  // Get assets by user
  getAssetsByUser: async (user) => {
    const response = await api.get(`/api/assets/list/user/${user}`);
    return response.data;
  },
};

// Registration API functions
export const registrationApi = {
  // Upload image
  uploadImage: async (file, onUploadProgress = null) => {
    const formData = new FormData();
    formData.append('file', file);

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    };

    // Add upload progress callback if provided
    if (onUploadProgress) {
      config.onUploadProgress = onUploadProgress;
    }

    const response = await api.post('/api/registration/upload', formData, config);
    return response.data;
  },

  // Segment image
  segmentImage: async (imagePath, onDownloadProgress = null) => {
    const config = {};

    // Add download progress callback if provided
    if (onDownloadProgress) {
      config.onDownloadProgress = onDownloadProgress;
    }

    const response = await api.post('/api/registration/segment', { image_path: imagePath }, config);
    return response.data;
  },

  // Perform OCR
  performOcr: async (imagePath, segments = null, onDownloadProgress = null) => {
    const config = {};

    // Add download progress callback if provided
    if (onDownloadProgress) {
      config.onDownloadProgress = onDownloadProgress;
    }

    const response = await api.post('/api/registration/ocr', { 
      image_path: imagePath,
      segments
    }, config);
    return response.data;
  },

  // Register asset
  registerAsset: async (assetData, onDownloadProgress = null) => {
    const config = {};

    // Add download progress callback if provided
    if (onDownloadProgress) {
      config.onDownloadProgress = onDownloadProgress;
    }

    const response = await api.post('/api/registration/register', assetData, config);
    return response.data;
  },

  // Get chatbot assistance
  getChatbotAssistance: async (ocrResults = null, modelName = null, serialNumber = null, onDownloadProgress = null) => {
    const config = {};

    // Add download progress callback if provided
    if (onDownloadProgress) {
      config.onDownloadProgress = onDownloadProgress;
    }

    const response = await api.post('/api/registration/chatbot-assist', {
      ocr_results: ocrResults,
      model_name: modelName,
      serial_number: serialNumber
    }, config);
    return response.data;
  },

  // Get registration workflow
  getWorkflow: async () => {
    const response = await api.get('/api/registration/workflow');
    return response.data;
  },
};

// Dashboard API functions
export const dashboardApi = {
  // Get dashboard stats
  getStats: async () => {
    const response = await api.get('/api/dashboard/stats');
    return response.data;
  },

  // Get site assets
  getSiteAssets: async () => {
    const response = await api.get('/api/dashboard/site-assets');
    return response.data;
  },

  // Get chart data
  getChartData: async () => {
    const response = await api.get('/api/dashboard/chart-data');
    return response.data;
  },
};

// Chatbot API functions
export const chatbotApi = {
  // Send message to chatbot
  sendMessage: async (message) => {
    const response = await api.post('/api/chatbot/send', message);
    return response.data;
  },

  // Get chat history
  getHistory: async () => {
    const response = await api.get('/api/chatbot/history');
    return response.data;
  },

  // Clear chat history
  clearHistory: async () => {
    const response = await api.delete('/api/chatbot/history');
    return response.data;
  },

  // Get asset assistance
  getAssetAssistance: async (modelName = null, serialNumber = null, manufacturer = null) => {
    const response = await api.post('/api/chatbot/asset-assist', {
      model_name: modelName,
      serial_number: serialNumber,
      manufacturer: manufacturer
    });
    return response.data;
  },
};

// Label API functions
export const labelApi = {
  // Get all labels
  getLabels: async () => {
    const response = await api.get('/api/labels');
    return response.data;
  },

  // Get label by ID
  getLabelById: async (id) => {
    const response = await api.get(`/api/labels/${id}`);
    return response.data;
  },

  // Create label
  createLabel: async (labelData) => {
    const response = await api.post('/api/labels', labelData);
    return response.data;
  },

  // Update label
  updateLabel: async (id, labelData) => {
    const response = await api.put(`/api/labels/${id}`, labelData);
    return response.data;
  },

  // Delete label
  deleteLabel: async (id) => {
    const response = await api.delete(`/api/labels/${id}`);
    return response.data;
  },

  // Download label
  downloadLabel: async (id) => {
    const response = await api.get(`/api/labels/${id}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Print label
  printLabel: async (id) => {
    const response = await api.post(`/api/labels/${id}/print`);
    return response.data;
  },

  // Get label by asset ID
  getLabelByAssetId: async (assetId) => {
    const response = await api.get(`/api/labels/asset/${assetId}`);
    return response.data;
  },

  // Batch print labels
  batchPrintLabels: async (assetIds) => {
    const response = await api.get('/api/labels/batch/print', {
      params: { asset_ids: assetIds },
    });
    return response.data;
  },
};

export default api;
