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
        // PDF 多页结果：添加 id 和 pageNumber
        const results = [];
        this.pdfPages.forEach(page => {
          page.ocrResults.forEach((result, idx) => {
            results.push({
              ...result,
              id: `${page.pageNumber}-${idx}`,
              pageNumber: page.pageNumber
            });
          });
        });
        return results;
      } else {
        // 图片结果：添加 id
        return this.ocrResults.map((result, idx) => ({
          ...result,
          id: idx
        }));
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

        const response = await fetch('/api/v1/ocr', {
          method: 'POST',
          headers: headers,
          body: formData
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || '识别失败');
        }

        const result = await response.json();

        if (result.code !== 200) {
          throw new Error(result.message || '识别失败');
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
        this.pdfPages = data.pages.map(page => ({
          pageNumber: page.page_number,
          width: page.width,
          height: page.height,
          text: page.text,
          ocrResults: page.ocr_response || []
        }));
        this.fullText = this.pdfPages.map(p => p.text).join('\n\n');
      } else {
        // 图片结果
        this.imageWidth = data.width || this.imageWidth;
        this.imageHeight = data.height || this.imageHeight;
        this.ocrResults = data.ocr_response || [];
        this.fullText = data.text || '';
      }
    },

    copyText(text) {
      this.copyToClipboard(text);
      this.showToast('已复制文本', 'success');
    },

    copyAllText() {
      this.copyToClipboard(this.fullText);
      this.showToast('已复制全部文本', 'success');
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
