const { createApp } = Vue;

// 配置 PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js';

createApp({
  data() {
    return {
      apiKey: '',
      imageUrl: null,
      imageWidth: 0,
      imageHeight: 0,
      ocrResults: [],
      pdfPages: [],
      fullText: '',
      hoveredIndex: -1,
      loading: false,
      loadingText: '正在识别中，请稍候...',
      isDragging: false,
      hasFile: false,
      isPdf: false,
      currentFile: null,
      filePath: '',  // 保存临时文件路径（image_path 或 pdf_path）
      isEmbedding: false,  // 正在嵌入PDF的标记
      // 日志查看相关
      showLogsModal: false,
      logsContent: '',
      logsLoading: false,
      logsError: '',
      // 高级参数
      params: {
        removeWatermark: false,
        watermarkColor: '#FFFFFF',
        colorTolerance: 30,
        deskew: false
      }
    };
  },
  computed: {
    displayResults() {
      if (this.isPdf) {
        // PDF 多页结果：展平所有页面的结果
        const results = [];
        this.pdfPages.forEach(page => {
          if (page.ocrResults) {
            page.ocrResults.forEach((result) => {
              results.push(result);
            });
          }
        });
        return results;
      } else {
        // 图片结果：直接返回
        return this.ocrResults;
      }
    },
    dynamicFullText() {
      // 根据表格内容动态拼合完整文本
      if (this.isPdf) {
        // 按页分组
        const pageGroups = {};
        this.displayResults.forEach(result => {
          if (!result.deleted) {
            const pageNum = result.pageNumber;
            if (!pageGroups[pageNum]) {
              pageGroups[pageNum] = [];
            }
            pageGroups[pageNum].push(result.editedText || result.text);
          }
        });
        // 拼接，跨页保持空行
        return Object.keys(pageGroups)
          .sort((a, b) => a - b)
          .map(pageNum => pageGroups[pageNum].join('\n'))
          .join('\n\n');
      } else {
        // 图片结果
        return this.displayResults
          .filter(result => !result.deleted)
          .map(result => result.editedText || result.text)
          .join('\n');
      }
    }
  },
  mounted() {
    // 从 localStorage 加载 API Key
    this.apiKey = localStorage.getItem('ocr_api_key') || '';

    // 监听粘贴事件
    document.addEventListener('paste', this.handlePaste);
  },
  beforeUnmount() {
    document.removeEventListener('paste', this.handlePaste);
  },
  methods: {
    saveApiKey() {
      localStorage.setItem('ocr_api_key', this.apiKey);
    },

    handleDragOver() {
      this.isDragging = true;
    },

    handleDragLeave(e) {
      if (e.target === e.currentTarget) {
        this.isDragging = false;
      }
    },

    handleDrop(e) {
      this.isDragging = false;
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        this.processFile(files[0]);
      }
    },

    handleFileUpload(e) {
      const files = e.target.files;
      if (files.length > 0) {
        this.processFile(files[0]);
      }
    },

    handlePaste(e) {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.indexOf('image') !== -1) {
          const file = item.getAsFile();
          if (file) {
            this.processFile(file);
          }
          break;
        }
      }
    },

    async processFile(file) {
      if (!file) return;

      // 检查文件类型
      const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
      const isImage = file.type.startsWith('image/');

      if (!isPdf && !isImage) {
        this.showToast('不支持的文件格式', 'error');
        return;
      }

      this.currentFile = file;
      this.isPdf = isPdf;
      this.hasFile = true;
      this.ocrResults = [];
      this.pdfPages = [];
      this.fullText = '';

      if (isPdf) {
        await this.processPdf(file);
      } else {
        await this.processImage(file);
      }
    },

    async processImage(file) {
      // 显示图片预览
      const reader = new FileReader();
      reader.onload = (e) => {
        this.imageUrl = e.target.result;
        // 获取图片尺寸
        const img = new Image();
        img.onload = () => {
          this.imageWidth = img.width;
          this.imageHeight = img.height;
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);

      // 调用 OCR 接口
      await this.callOcrApi(file);
    },

    async processPdf(file) {
      this.loading = true;
      this.loadingText = '正在加载 PDF...';

      try {
        // 先调用 OCR 接口
        await this.callOcrApi(file);

        // 再渲染 PDF 预览
        const arrayBuffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

        this.loadingText = '正在渲染 PDF 页面...';

        // 渲染每一页
        for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
          const page = await pdf.getPage(pageNum);
          await this.$nextTick();

          const canvas = document.getElementById(`pdf-canvas-${pageNum}`);
          if (!canvas) continue;

          const context = canvas.getContext('2d');
          const viewport = page.getViewport({ scale: 1.5 });

          canvas.width = viewport.width;
          canvas.height = viewport.height;

          await page.render({
            canvasContext: context,
            viewport: viewport
          }).promise;
        }
      } catch (error) {
        console.error('PDF 处理失败:', error);
        this.showToast('PDF 加载失败', 'error');
      } finally {
        this.loading = false;
      }
    },

    async callOcrApi(file) {
      this.loading = true;
      this.loadingText = '正在识别中，请稍候...';

      const formData = new FormData();
      formData.append('file', file);

      // 添加高级参数
      formData.append('remove_watermark', this.params.removeWatermark ? 'true' : 'false');
      formData.append('deskew', this.params.deskew ? 'true' : 'false');

      // 如果启用了水印移除，添加水印颜色和容差
      if (this.params.removeWatermark) {
        formData.append('watermark_color', this.params.watermarkColor);
        formData.append('watermark_tolerance', this.params.colorTolerance.toString());
      }

      try {
        const headers = {};
        if (this.apiKey) {
          headers['Authorization'] = `Bearer ${this.apiKey}`;
        }

        const response = await fetch('/api/ocr', {
          method: 'POST',
          headers: headers,
          body: formData
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || '识别失败');
        }

        const result = await response.json();

        // 检查响应格式：后端返回 { "success": true/false, "data": {...} }
        if (!result.success) {
          throw new Error(result.error?.message || result.message || '识别失败');
        }

        // 处理响应数据
        this.processOcrResult(result.data);
        this.showToast('识别完成！', 'success');

      } catch (error) {
        console.error('OCR 识别失败:', error);
        this.showToast(error.message || '识别失败', 'error');
      } finally {
        if (!this.isPdf) {
          this.loading = false;
        }
      }
    },

    processOcrResult(data) {
      if (data.pages) {
        // PDF 多页结果
        this.pdfPages = data.pages.map(page => {
          // 优先使用预处理后的图片（如果存在）
          let previewImageUrl = null;
          if (page.processed_image_path) {
            // 提取文件名（去掉路径前缀）
            const filename = page.processed_image_path.split('/').pop();
            // 构建服务端图片URL，带上API Key（如果有）
            previewImageUrl = `/api/temp/${filename}${this.apiKey ? '?api_key=' + this.apiKey : ''}`;
          }

          return {
            pageNumber: page.page_number,
            width: page.width,
            height: page.height,
            text: page.text,
            processedImagePath: page.processed_image_path,  // 保存预处理图片路径
            previewImageUrl: previewImageUrl,  // 新增：预览图片URL
            ocrResults: (page.ocr_response || []).map((result, idx) => ({
              ...result,
              id: `${page.page_number}-${idx}`,
              pageNumber: page.page_number,
              deleted: false,
              editedText: result.text
            }))
          };
        });
        this.fullText = this.pdfPages.map(p => p.text).join('\n\n');
        this.filePath = data.pdf_path || '';  // 保存 PDF 路径
      } else {
        // 图片结果
        this.imageWidth = data.width || this.imageWidth;
        this.imageHeight = data.height || this.imageHeight;
        this.ocrResults = (data.ocr_response || []).map((result, idx) => ({
          ...result,
          id: idx,
          deleted: false,
          editedText: result.text
        }));
        this.fullText = data.text || '';
        this.filePath = data.image_path || '';  // 保存图片路径

        // 图片模式：优先使用预处理后的图片（使用与 PDF 一致的字段名）
        if (data.processed_image_path) {
          const filename = data.processed_image_path.split('/').pop();
          const serverImageUrl = `/api/temp/${filename}${this.apiKey ? '?api_key=' + this.apiKey : ''}`;

          // 使用服务端预处理图片替换本地图片
          this.imageUrl = serverImageUrl;
          console.log('使用服务端预处理图片:', serverImageUrl);
        }
        // 否则继续使用本地图片（this.imageUrl 已在 processImage 中设置）
      }
    },

    copyText(text) {
      this.copyToClipboard(text);
      this.showToast('已复制文本', 'success');
    },

    copyAllText() {
      this.copyToClipboard(this.dynamicFullText);
      this.showToast('已复制全部文本', 'success');
    },

    // 编辑文本
    updateText(result, newText) {
      // 直接修改对象属性，Vue 3 会自动追踪
      result.editedText = newText.trim();
    },

    // 删除行
    deleteRow(result) {
      result.deleted = true;
    },

    // 还原行
    restoreRow(result) {
      result.deleted = false;
    },

    // 嵌入并下载PDF
    async embedAndDownloadPdf() {
      // 防止重复点击
      if (this.isEmbedding) {
        this.showToast('正在处理中，请稍候...', 'info');
        return;
      }

      if (!this.filePath) {
        this.showToast('没有可用的文件路径', 'error');
        return;
      }

      this.isEmbedding = true;  // 标记开始处理
      this.loading = true;
      this.loadingText = '正在生成PDF...';

      try {
        // 构建请求数据
        const requestData = {
          file_path: this.filePath,
          file_type: this.isPdf ? 'pdf' : 'image',
          apply_preprocessing: true  // 默认使用预处理后的图片（去水印/纠偏）
        };

        if (this.isPdf) {
          // PDF 模式：发送 pages 数组
          requestData.pages = this.pdfPages.map(page => ({
            page_number: page.pageNumber,
            width: page.width,
            height: page.height,
            processed_image_path: page.processedImagePath,  // 传递预处理图片路径
            ocr_response: this.displayResults
              .filter(r => r.pageNumber === page.pageNumber && !r.deleted)
              .map(r => ({
                text: r.editedText || r.text,
                rate: r.rate,
                left: r.left,
                top: r.top,
                right: r.right,
                bottom: r.bottom
              }))
          }));
        } else {
          // 图片模式：发送 ocr_response 数组
          requestData.ocr_response = this.displayResults
            .filter(r => !r.deleted)
            .map(r => ({
              text: r.editedText || r.text,
              rate: r.rate,
              left: r.left,
              top: r.top,
              right: r.right,
              bottom: r.bottom
            }));
        }

        const headers = {
          'Content-Type': 'application/json'
        };
        if (this.apiKey) {
          headers['Authorization'] = `Bearer ${this.apiKey}`;
        }

        const response = await fetch('/api/embed', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(requestData)
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || '生成PDF失败');
        }

        // 下载PDF文件
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ocr_embedded_${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        this.showToast('PDF已生成并开始下载', 'success');

      } catch (error) {
        console.error('生成PDF失败:', error);
        this.showToast(error.message || '生成PDF失败', 'error');
      } finally {
        this.isEmbedding = false;  // 恢复按钮状态
        this.loading = false;
      }
    },

    copyToClipboard(text) {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text);
      } else {
        // 降级方案
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
          document.execCommand('copy');
        } catch (error) {
          console.error('复制失败:', error);
        }
        document.body.removeChild(textArea);
      }
    },

    async viewLogs() {
      // 检查是否配置了 API Key
      if (!this.apiKey) {
        this.showToast('请先配置 API Key', 'error');
        return;
      }

      this.showLogsModal = true;
      this.logsLoading = true;
      this.logsError = '';
      this.logsContent = '';

      try {
        const response = await fetch('/api/logs', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${this.apiKey}`
          }
        });

        const result = await response.json();

        if (response.ok && result.success) {
          this.logsContent = result.data.logs.join('\n');
        } else {
          this.logsError = result.error?.message || '获取日志失败';
        }
      } catch (error) {
        console.error('获取日志失败:', error);
        this.logsError = `网络错误: ${error.message}`;
      } finally {
        this.logsLoading = false;
      }
    },

    async refreshLogs() {
      this.logsLoading = true;
      this.logsError = '';

      try {
        const response = await fetch('/api/logs', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${this.apiKey}`
          }
        });

        const result = await response.json();

        if (response.ok && result.success) {
          this.logsContent = result.data.logs.join('\n');
          this.showToast('日志已刷新', 'success');
        } else {
          this.logsError = result.error?.message || '获取日志失败';
        }
      } catch (error) {
        console.error('刷新日志失败:', error);
        this.logsError = `网络错误: ${error.message}`;
      } finally {
        this.logsLoading = false;
      }
    },

    showToast(message, type = 'info') {
      const backgroundColor = type === 'success' ? '#67c23a' : type === 'error' ? '#f56c6c' : '#409EFF';
      Toastify({
        text: message,
        duration: 3000,
        gravity: 'top',
        position: 'center',
        style: {
          background: backgroundColor
        }
      }).showToast();
    }
  }
}).mount('#app');
