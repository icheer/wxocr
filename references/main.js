const { createApp } = Vue

const app = createApp({
  data() {
    return {
      imageUrl: '',
      ocrResults: [],
      imageWidth: 0,
      imageHeight: 0,
      loading: false,
      isDragging: false,
      hoveredIndex: -1,
      clipboard: null
    };
  },
  computed: {
    isMobile() {
      return window.innerWidth <= 768;
    },
    isPC() {
      return !this.isMobile;
    }
  },
  mounted() {
    // 初始化clipboard实例
    this.clipboard = new ClipboardJS('.ocr-box', {
      text: trigger => {
        return trigger.getAttribute('data-text');
      }
    });

    // 监听复制成功事件
    this.clipboard.on('success', e => {
      e.clearSelection();
      Toastify({
        text: '文字已复制到剪贴板',
        duration: 2000,
        gravity: 'top',
        position: 'right',
        backgroundColor: '#4CAF50',
        stopOnFocus: true
      }).showToast();
    });

    // 监听复制失败事件
    this.clipboard.on('error', e => {
      Toastify({
        text: '复制失败，请重试',
        duration: 2000,
        gravity: 'top',
        position: 'right',
        backgroundColor: '#f44336',
        stopOnFocus: true
      }).showToast();
    });

    // 阻止全局拖拽事件
    document.addEventListener(
      'dragover',
      e => {
        e.preventDefault();
        if (!e.target.closest('.upload-area')) {
          document.body.classList.add('dragging');
        }
      },
      false
    );

    document.addEventListener(
      'drop',
      e => {
        e.preventDefault();
        document.body.classList.remove('dragging');
      },
      false
    );

    document.addEventListener(
      'dragleave',
      e => {
        if (!e.target.closest('.upload-area')) {
          document.body.classList.remove('dragging');
        }
      },
      false
    );

    // 页面中按下Ctrl+V时粘贴图片到上传区域
    document.addEventListener('paste', e => {
      const items = e.clipboardData.items;
      if (!items.length) return;

      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === 'file' && items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile();
          this.processFile(file);
          break;
        }
      }
    });
  },
  beforeUnmount() {
    // 销毁clipboard实例
    if (this.clipboard) {
      this.clipboard.destroy();
    }
    // 移除全局拖拽事件监听
    document.removeEventListener('dragover', e => e.preventDefault());
    document.removeEventListener('drop', e => e.preventDefault());
    document.removeEventListener('dragleave', e => e.preventDefault());
  },
  methods: {
    handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      this.processFile(file);
    },

    handleDragOver(event) {
      this.isDragging = true;
    },

    handleDragLeave(event) {
      // 检查是否真的离开了upload-area区域
      const rect = event.currentTarget.getBoundingClientRect();
      const x = event.clientX;
      const y = event.clientY;

      if (
        x <= rect.left ||
        x >= rect.right ||
        y <= rect.top ||
        y >= rect.bottom
      ) {
        this.isDragging = false;
      }
    },

    handleDrop(event) {
      this.isDragging = false;

      const file = event.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        this.processFile(file);
      }
    },

    copyText(text) {
      // 创建一个临时元素来触发复制
      const tempElement = document.createElement('div');
      tempElement.setAttribute('data-clipboard-text', text);
      document.body.appendChild(tempElement);

      // 创建新的clipboard实例
      const clipboard = new ClipboardJS(tempElement);

      // 触发复制
      clipboard.on('success', e => {
        e.clearSelection();
        Toastify({
          text: '文字已复制到剪贴板',
          duration: 2000,
          gravity: 'top',
          position: 'right',
          backgroundColor: '#4CAF50',
          stopOnFocus: true
        }).showToast();
      });

      clipboard.on('error', e => {
        Toastify({
          text: '复制失败，请重试',
          duration: 2000,
          gravity: 'top',
          position: 'right',
          backgroundColor: '#f44336',
          stopOnFocus: true
        }).showToast();
      });

      // 触发点击事件
      tempElement.click();

      // 清理
      setTimeout(() => {
        document.body.removeChild(tempElement);
        clipboard.destroy();
      }, 100);
    },

    processFile(file) {
      const reader = new FileReader();
      reader.onload = e => {
        this.imageUrl = e.target.result;
        // 获取图片尺寸
        const img = new Image();
        img.onload = () => {
          this.imageWidth = img.width;
          this.imageHeight = img.height;
        };
        img.src = e.target.result;

        // 发送OCR请求
        this.sendOCRRequest(e.target.result);
      };
      reader.readAsDataURL(file);
    },

    async sendOCRRequest(base64Image) {
      this.loading = true;
      this.ocrResults = [];
      let data = null;
      try {
        const response = await fetch('/wxocr/ocr', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            image: base64Image.split(',')[1] // 移除base64头部信息
          })
        });
        data = await response.json();
      } catch (error) {
        console.error('OCR请求失败:', error);
        // data = mockResponse;
      } finally {
        this.loading = false;
      }
      if (data.result && data.result.ocr_response) {
        this.ocrResults = data.result.ocr_response;
      }
      if (!this.ocrResults.length) {
        Toastify({
          text: '未能识别到图片中的文字',
          duration: 2000,
          gravity: 'top',
          position: 'right',
          backgroundColor: '#f44336',
          stopOnFocus: true
        }).showToast();
      }
    }
  }
});

app.mount('#app');

// 图片发送至接口后,得到的OCR结果响应报文
var mockResponse = {
  result: {
    errcode: 0,
    height: 591,
    imgpath: 'temp/7e640f5c-e915-4a2d-9163-324111654a1d.png',
    ocr_response: [
      {
        bottom: 38.32209396362305,
        left: 23.225812911987305,
        rate: 0.9896392226219177,
        right: 443.50152587890625,
        text: 'java-opencv体验微信二维码检测解码',
        top: 11.27866268157959
      },
      {
        bottom: 77.17500305175781,
        left: 24.5,
        rate: 0.9706559181213379,
        right: 493.6750183105469,
        text: '原创 冒泡的肥皂 冒泡的肥皂 2024年04月14日 17:08 北京',
        top: 56.35000228881836
      },
      {
        bottom: 143.3249969482422,
        left: 22.05000114440918,
        rate: 0.6095524430274963,
        right: 68.5999984741211,
        text: '前音',
        top: 116.375
      },
      {
        bottom: 172.15647888183594,
        left: 34.28524398803711,
        rate: 0.9945204257965088,
        right: 770.5447998046875,
        text: '维码的使用无处不在，掏出手机扫一扫。opencv contrib是作为opencv的扩展模块',
        top: 148.19985961914062
      },
      {
        bottom: 199.6750030517578,
        left: 23.274999618530273,
        rate: 0.9759628176689148,
        right: 764.4000244140625,
        text: '独立存在的，这里面有包含一些新的算法或者有专利的。腾讯WeChatcV团队贡献了',
        top: 178.85000610351562
      },
      {
        bottom: 231.8022003173828,
        left: 23.243066787719727,
        rate: 0.9887627959251404,
        right: 760.748291015625,
        text: 'wechat qrcode模块。因为是在扩展模块所以需要自己手动编译把扩展模块加载进去。',
        top: 206.771728515625
      },
      {
        bottom: 260.93121337890625,
        left: 23.256383895874023,
        rate: 0.9992458820343018,
        right: 770.5437622070312,
        text: '网上看到的是腾讯的二维码识别效率非常高，自己编译使用可以轻松拥有微信扫码般的',
        top: 237.62925720214844
      },
      {
        bottom: 291.5500183105469,
        left: 22.05000114440918,
        rate: 0.999659538269043,
        right: 111.4749984741211,
        text: '功能体验。',
        top: 267.0500183105469
      },
      {
        bottom: 347.8999938964844,
        left: 23.274999618530273,
        rate: 0.9959022998809814,
        right: 200.90000915527344,
        text: 'win下opencv编译',
        top: 325.8500061035156
      },
      {
        bottom: 378.5249938964844,
        left: 22.05000114440918,
        rate: 0.9922881126403809,
        right: 770.5250244140625,
        text: '0.工具就是cmake和Visual studio;编译很简单跟着教程安装工具跟着配置走就行',
        top: 355.25
      },
      {
        bottom: 437.32501220703125,
        left: 23.274999618530273,
        rate: 0.9965458512306213,
        right: 322.1750183105469,
        text: '1.网上教程很多，我参考的是这篇',
        top: 416.5
      },
      {
        bottom: 467.95001220703125,
        left: 23.274999618530273,
        rate: 0.9960957169532776,
        right: 769.2999877929688,
        text: '2.基础包在github上下就可以了。注意版本要一致。opecv下载，opencv contrib下',
        top: 445.8999938964844
      },
      {
        bottom: 494.9000244140625,
        left: 44.10000228881836,
        rate: 0.986846387386322,
        right: 71.05000305175781,
        text: '载',
        top: 476.5250244140625
      },
      {
        bottom: 526.8564453125,
        left: 23.23899269104004,
        rate: 0.9930692315101624,
        right: 523.108154296875,
        text: '3.github网络是要通的的，因为一些依赖需要从这里下的;',
        top: 503.59161376953125
      },
      {
        bottom: 556.1500244140625,
        left: 22.05000114440918,
        rate: 0.9987644553184509,
        right: 770.5250244140625,
        text: '4.文件路径要用英文的，不然会有些问题。用工具有时想用个中文的文件名感觉经常会',
        top: 534.1000366210938
      },
      {
        bottom: 585.5499877929688,
        left: 46.54999923706055,
        rate: 0.999256432056427,
        right: 306.25,
        text: '遇到文件路径识别乱码的问题。',
        top: 564.7250366210938
      }
    ],
    width: 784
  }
};
